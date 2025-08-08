from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from ..models.database import get_db
from ..models.schemas import (
    CareerPageConfigCreate, CareerPageConfigUpdate, CareerPageConfigResponse
)
from ..services.career_page_scraping_service import CareerPageScrapingService
from ..routes.auth import get_current_user_dependency
from ..models.models import User, CareerPageConfig
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/career-pages", tags=["career-pages"])

# Initialize services
scraping_service = CareerPageScrapingService()

@router.post("/", response_model=CareerPageConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_career_page_config(
    config_data: CareerPageConfigCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency)
):
    """Create a new career page configuration"""
    try:
        # Check if config already exists for this company and user
        existing_config = db.query(CareerPageConfig).filter(
            CareerPageConfig.user_id == current_user.id,
            CareerPageConfig.company_name == config_data.company_name
        ).first()
        
        if existing_config:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Career page configuration already exists for {config_data.company_name}"
            )
        
        # Create new config
        career_config = CareerPageConfig(
            user_id=current_user.id,
            company_name=config_data.company_name,
            career_url=config_data.career_url,
            scrape_frequency=config_data.scrape_frequency,
            scraping_rules=config_data.scraping_rules,
            authentication_data=config_data.authentication_data,
            is_active=True,
            jobs_found_count=0
        )
        
        db.add(career_config)
        db.commit()
        db.refresh(career_config)
        
        logger.info(f"Created career page config for {config_data.company_name}")
        
        return CareerPageConfigResponse(
            id=career_config.id,
            user_id=career_config.user_id,
            company_name=career_config.company_name,
            career_url=career_config.career_url,
            scrape_frequency=career_config.scrape_frequency,
            is_active=career_config.is_active,
            last_scraped=career_config.last_scraped,
            last_success=career_config.last_success,
            error_message=career_config.error_message,
            jobs_found_count=career_config.jobs_found_count,
            created_at=career_config.created_at,
            updated_at=career_config.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating career page config: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create career page configuration"
        )

@router.get("/", response_model=List[CareerPageConfigResponse])
async def get_career_page_configs(
    skip: int = Query(0, ge=0, description="Number of configs to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of configs to return"),
    company: Optional[str] = Query(None, description="Filter by company name"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency)
):
    """Get career page configurations for the current user"""
    try:
        query = db.query(CareerPageConfig).filter(CareerPageConfig.user_id == current_user.id)
        
        if company:
            query = query.filter(CareerPageConfig.company_name.ilike(f"%{company}%"))
        
        if is_active is not None:
            query = query.filter(CareerPageConfig.is_active == is_active)
        
        configs = query.offset(skip).limit(limit).all()
        
        return [
            CareerPageConfigResponse(
                id=config.id,
                user_id=config.user_id,
                company_name=config.company_name,
                career_url=config.career_url,
                scrape_frequency=config.scrape_frequency,
                is_active=config.is_active,
                last_scraped=config.last_scraped,
                last_success=config.last_success,
                error_message=config.error_message,
                jobs_found_count=config.jobs_found_count,
                created_at=config.created_at,
                updated_at=config.updated_at
            )
            for config in configs
        ]
        
    except Exception as e:
        logger.error(f"Error getting career page configs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve career page configurations"
        )

@router.get("/{config_id}", response_model=CareerPageConfigResponse)
async def get_career_page_config(
    config_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency)
):
    """Get a specific career page configuration"""
    try:
        config = db.query(CareerPageConfig).filter(
            CareerPageConfig.id == config_id,
            CareerPageConfig.user_id == current_user.id
        ).first()
        
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Career page configuration not found"
            )
        
        return CareerPageConfigResponse(
            id=config.id,
            user_id=config.user_id,
            company_name=config.company_name,
            career_url=config.career_url,
            scrape_frequency=config.scrape_frequency,
            is_active=config.is_active,
            last_scraped=config.last_scraped,
            last_success=config.last_success,
            error_message=config.error_message,
            jobs_found_count=config.jobs_found_count,
            created_at=config.created_at,
            updated_at=config.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting career page config {config_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve career page configuration"
        )

@router.put("/{config_id}", response_model=CareerPageConfigResponse)
async def update_career_page_config(
    config_id: int,
    config_update: CareerPageConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency)
):
    """Update an existing career page configuration"""
    try:
        config = db.query(CareerPageConfig).filter(
            CareerPageConfig.id == config_id,
            CareerPageConfig.user_id == current_user.id
        ).first()
        
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Career page configuration not found"
            )
        
        # Update fields
        update_data = config_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(config, field):
                setattr(config, field, value)
        
        from datetime import datetime
        config.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(config)
        
        logger.info(f"Updated career page config for {config.company_name}")
        
        return CareerPageConfigResponse(
            id=config.id,
            user_id=config.user_id,
            company_name=config.company_name,
            career_url=config.career_url,
            scrape_frequency=config.scrape_frequency,
            is_active=config.is_active,
            last_scraped=config.last_scraped,
            last_success=config.last_success,
            error_message=config.error_message,
            jobs_found_count=config.jobs_found_count,
            created_at=config.created_at,
            updated_at=config.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating career page config {config_id}: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update career page configuration"
        )

@router.delete("/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_career_page_config(
    config_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency)
):
    """Delete a career page configuration"""
    try:
        config = db.query(CareerPageConfig).filter(
            CareerPageConfig.id == config_id,
            CareerPageConfig.user_id == current_user.id
        ).first()
        
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Career page configuration not found"
            )
        
        db.delete(config)
        db.commit()
        
        logger.info(f"Deleted career page config for {config.company_name}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting career page config {config_id}: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete career page configuration"
        )

@router.post("/{config_id}/scrape")
async def scrape_career_page(
    config_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency)
):
    """Manually trigger scraping for a specific career page"""
    try:
        config = db.query(CareerPageConfig).filter(
            CareerPageConfig.id == config_id,
            CareerPageConfig.user_id == current_user.id
        ).first()
        
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Career page configuration not found"
            )
        
        # Perform scraping
        scrape_result = await scraping_service.scrape_career_page(config)
        
        # Update configuration with results
        from datetime import datetime
        config.last_scraped = datetime.utcnow()
        config.last_success = scrape_result['success']
        
        if scrape_result['success']:
            # Save jobs to database
            save_stats = await scraping_service.save_jobs_to_database(
                scrape_result['jobs'], config.company_name, db
            )
            config.jobs_found_count = scrape_result['jobs_found']
            config.error_message = None
            
            db.commit()
            
            return {
                "success": True,
                "jobs_found": scrape_result['jobs_found'],
                "save_stats": save_stats,
                "scraped_at": scrape_result['scraped_at']
            }
        else:
            config.error_message = scrape_result['error']
            db.commit()
            
            return {
                "success": False,
                "error": scrape_result['error'],
                "scraped_at": scrape_result['scraped_at']
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error scraping career page {config_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to scrape career page"
        )

@router.post("/scrape-all")
async def scrape_all_active_pages(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency)
):
    """Scrape all active career pages for the current user"""
    try:
        results = await scraping_service.scrape_and_save_all_configured_pages(
            current_user.id, db
        )
        return results
    except Exception as e:
        logger.error(f"Error scraping all career pages: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to scrape all career pages"
        )

@router.post("/{config_id}/test")
async def test_career_page_scraping(
    config_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency)
):
    """Test scraping for a career page without saving results"""
    try:
        config = db.query(CareerPageConfig).filter(
            CareerPageConfig.id == config_id,
            CareerPageConfig.user_id == current_user.id
        ).first()
        
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Career page configuration not found"
            )
        
        # Perform test scraping (don't save results)
        scrape_result = await scraping_service.scrape_career_page(config)
        
        # Return results without saving
        return {
            "test_mode": True,
            "success": scrape_result['success'],
            "jobs_found": scrape_result['jobs_found'],
            "jobs": scrape_result['jobs'][:5] if scrape_result['jobs'] else [],  # Show first 5 jobs
            "error": scrape_result.get('error'),
            "scraped_at": scrape_result['scraped_at']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing career page scraping {config_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to test career page scraping"
        )

@router.get("/analytics/scraping-stats")
async def get_scraping_analytics(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency)
):
    """Get scraping analytics for the current user's career pages"""
    try:
        from datetime import datetime, timedelta
        from sqlalchemy import func, and_
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Get all configs for user
        configs = db.query(CareerPageConfig).filter(
            CareerPageConfig.user_id == current_user.id
        ).all()
        
        # Calculate stats
        total_configs = len(configs)
        active_configs = len([c for c in configs if c.is_active])
        
        # Recent scraping activity
        recent_scrapes = [c for c in configs if c.last_scraped and c.last_scraped >= cutoff_date]
        successful_scrapes = [c for c in recent_scrapes if c.last_success]
        
        # Jobs found statistics
        total_jobs_found = sum(c.jobs_found_count for c in configs)
        
        return {
            "total_configurations": total_configs,
            "active_configurations": active_configs,
            "recent_scrapes": len(recent_scrapes),
            "successful_scrapes": len(successful_scrapes),
            "total_jobs_found": total_jobs_found,
            "companies": [c.company_name for c in configs],
            "days_analyzed": days
        }
        
    except Exception as e:
        logger.error(f"Error getting scraping analytics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve scraping analytics"
        )