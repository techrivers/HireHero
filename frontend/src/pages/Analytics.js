import React, { useState, useEffect } from 'react';
import axios from 'axios';
import API_CONFIG from '../config/api';
import DashboardCard, { StatCard } from '../components/DashboardCard';
import { 
  BarChart3, 
  TrendingUp, 
  Users, 
  Target,
  Award,
  Calendar
} from 'lucide-react';
import './Analytics.css';

const Analytics = () => {
  const [analytics, setAnalytics] = useState(null);
  const [trends, setTrends] = useState(null);
  const [skillAnalysis, setSkillAnalysis] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    axios.defaults.baseURL = API_CONFIG.baseURL;
    fetchAnalyticsData();
  }, []);

  const fetchAnalyticsData = async () => {
    try {
      const responses = await Promise.allSettled([
        axios.get('/analytics/dashboard-stats'),
        axios.get('/analytics/match-trends?days=30'),
        axios.get('/analytics/skill-analysis')
      ]);

      // Handle each response individually
      if (responses[0].status === 'fulfilled') {
        setAnalytics(responses[0].value.data);
      } else {
        console.error('Dashboard stats failed:', responses[0].reason);
        setAnalytics({
          matches_this_month: 0,
          matches_this_week: 0,
          success_rate: 0,
          avg_match_score: 0
        });
      }

      if (responses[1].status === 'fulfilled') {
        setTrends(responses[1].value.data);
      } else {
        console.error('Trends failed:', responses[1].reason);
        setTrends({
          total_matches: 0,
          total_candidates: 0
        });
      }

      if (responses[2].status === 'fulfilled') {
        setSkillAnalysis(responses[2].value.data);
      } else {
        console.error('Skill analysis failed:', responses[2].reason);
        setSkillAnalysis({
          most_demanded_skills: [],
          skill_gaps: []
        });
      }
    } catch (error) {
      console.error('Error fetching analytics data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="analytics-loading">
        <div className="spinner-large"></div>
        <p>Loading analytics...</p>
      </div>
    );
  }

  return (
    <div className="analytics-page">
      <div className="page-container">
        <div className="page-header">
          <h1 className="page-title">Analytics</h1>
          <p className="page-subtitle">
            Insights and metrics for your recruitment process
          </p>
        </div>

        {/* Key Metrics */}
        {analytics && (
          <div className="dashboard-grid four-columns">
            <StatCard
              title="This Month"
              value={analytics.matches_this_month}
              icon={Calendar}
              className="stat-primary"
            />
            
            <StatCard
              title="This Week" 
              value={analytics.matches_this_week}
              icon={TrendingUp}
              className="stat-success"
            />
            
            <StatCard
              title="Success Rate"
              value={`${analytics.success_rate}%`}
              icon={Award}
              className="stat-warning"
            />
            
            <StatCard
              title="Avg Score"
              value={`${analytics.avg_match_score}%`}
              icon={Target}
              className="stat-info"
            />
          </div>
        )}

        <div className="dashboard-grid two-columns">
          {/* Match Trends */}
          {trends && (
            <DashboardCard title="Match Trends (30 Days)" icon={BarChart3}>
              <div className="trends-summary">
                <div className="trend-item">
                  <span className="trend-label">Total Matches</span>
                  <span className="trend-value">{trends.total_matches}</span>
                </div>
                <div className="trend-item">
                  <span className="trend-label">Total Candidates</span>
                  <span className="trend-value">{trends.total_candidates}</span>
                </div>
                <div className="trend-item">
                  <span className="trend-label">Avg per Match</span>
                  <span className="trend-value">
                    {trends.total_matches > 0 
                      ? Math.round(trends.total_candidates / trends.total_matches)
                      : 0
                    }
                  </span>
                </div>
              </div>
            </DashboardCard>
          )}

          {/* Skill Analysis */}
          {skillAnalysis && (
            <DashboardCard title="Most Demanded Skills" icon={Users}>
              <div className="skills-list">
                {skillAnalysis.most_demanded_skills.slice(0, 8).map((skill, index) => (
                  <div key={index} className="skill-item">
                    <span className="skill-name">{skill.skill}</span>
                    <div className="skill-bar">
                      <div 
                        className="skill-fill" 
                        style={{ 
                          width: `${(skill.demand / Math.max(...skillAnalysis.most_demanded_skills.map(s => s.demand))) * 100}%` 
                        }}
                      ></div>
                    </div>
                    <span className="skill-count">{skill.demand}</span>
                  </div>
                ))}
              </div>
            </DashboardCard>
          )}
        </div>

        {/* Skill Gaps */}
        {skillAnalysis && skillAnalysis.skill_gaps && skillAnalysis.skill_gaps.length > 0 && (
          <DashboardCard title="Skills in High Demand" icon={TrendingUp}>
            <p className="card-description">
              Skills with highest demand-to-supply ratio in your recent matches
            </p>
            <div className="skill-gaps">
              {skillAnalysis.skill_gaps.map((gap, index) => (
                <div key={index} className="gap-item">
                  <div className="gap-info">
                    <span className="gap-skill">{gap.skill}</span>
                    <span className="gap-ratio">Gap Ratio: {gap.gap_ratio}x</span>
                  </div>
                  <div className="gap-details">
                    <span className="gap-demand">Demand: {gap.demand}</span>
                    <span className="gap-supply">Supply: {gap.supply}</span>
                  </div>
                </div>
              ))}
            </div>
          </DashboardCard>
        )}
      </div>
    </div>
  );
};

export default Analytics;