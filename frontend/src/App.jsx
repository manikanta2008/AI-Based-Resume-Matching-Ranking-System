import { useState, useEffect } from "react";
import AddJob from "./pages/AddJob";
import UploadResumes from "./pages/UploadResumes";
import CandidateMatching from "./pages/CandidateMatching";
import api from "./services/api";
import "./App.css";

function App() {
  const [activePage, setActivePage] = useState("Dashboard");
  const [selectedJobId, setSelectedJobId] = useState(null);

  const [stats, setStats] = useState({
    totalJobs: 0,
    totalResumes: 0,
    topMatch: "--",
    recentJobs: [],
  });

  useEffect(() => {
    fetchDashboardStats();
  }, [activePage]);

  const fetchDashboardStats = async () => {
    try {
      const [jobsRes, resumesRes] = await Promise.all([
        api.get("/jobs").catch(() => ({ data: [] })),
        api.get("/resumes").catch(() => ({ data: [] })),
      ]);

      const jobs = jobsRes.data || [];
      const resumes = resumesRes.data || [];

      let topScore = "--";
      if (jobs.length > 0) {
        try {
          const rankingsRes = await api.get(`/resumes/rankings/${jobs[0].id}`);
          if (rankingsRes.data?.ranked_candidates?.length > 0) {
            topScore = `${Math.round(rankingsRes.data.ranked_candidates[0].overall_score)}%`;
          }
        } catch {
          // No ranking yet
        }
      }

      setStats({
        totalJobs: jobs.length,
        totalResumes: resumes.length,
        topMatch: topScore,
        recentJobs: jobs.slice(0, 5),
      });
    } catch {
      // Ignore initial stats load errors
    }
  };

  const openCandidateMatching = (jobId = null) => {
    if (jobId) setSelectedJobId(jobId);
    setActivePage("Candidate Matching");
  };

  return (
    <div className="app-container">
      {/* Clean Simple Navigation Header */}
      <nav className="navbar">
        <div className="navbar-brand">
          <span className="navbar-title">AI Resume Parser & Matcher</span>
        </div>

        <div className="navbar-nav">
          <button
            className={`nav-link ${activePage === "Dashboard" ? "active" : ""}`}
            onClick={() => setActivePage("Dashboard")}
          >
            Dashboard
          </button>
          <button
            className={`nav-link ${activePage === "Job Descriptions" ? "active" : ""}`}
            onClick={() => setActivePage("Job Descriptions")}
          >
            Job Descriptions
          </button>
          <button
            className={`nav-link ${activePage === "Upload Resumes" ? "active" : ""}`}
            onClick={() => setActivePage("Upload Resumes")}
          >
            Upload Resumes
          </button>
          <button
            className={`nav-link ${activePage === "Candidate Matching" ? "active" : ""}`}
            onClick={() => openCandidateMatching()}
          >
            Candidate Matching
          </button>
        </div>
      </nav>

      {/* Main Page Content */}
      <main className="main-content">
        {activePage === "Dashboard" ? (
          <div>
            <div className="page-header">
              <h1 className="page-title">Recruitment Dashboard</h1>
              <p className="page-desc">
                Automated resume parsing, requirement extraction, candidate ranking, and semantic matching.
              </p>
            </div>

            {/* Stats Overview */}
            <div className="stats-grid">
              <div className="stat-box">
                <div className="stat-label">Job Descriptions</div>
                <div className="stat-value">{stats.totalJobs}</div>
                <div className="stat-desc">Parsed and saved in database</div>
              </div>

              <div className="stat-box">
                <div className="stat-label">Resumes Uploaded</div>
                <div className="stat-value">{stats.totalResumes}</div>
                <div className="stat-desc">Candidate profiles extracted</div>
              </div>

              <div className="stat-box">
                <div className="stat-label">Top Match Score</div>
                <div className="stat-value">{stats.topMatch}</div>
                <div className="stat-desc">Highest candidate matching score</div>
              </div>

              <div className="stat-box">
                <div className="stat-label">Matching Engine</div>
                <div className="stat-value" style={{ fontSize: "20px", marginTop: "12px", color: "#16a34a" }}>
                  Active
                </div>
                <div className="stat-desc">Semantic similarity & NLP active</div>
              </div>
            </div>

            {/* Quick Actions */}
            <div className="card">
              <div className="card-title">Quick Actions</div>
              <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
                <button
                  className="btn btn-primary"
                  onClick={() => setActivePage("Job Descriptions")}
                >
                  + Add Job Description
                </button>
                <button
                  className="btn btn-secondary"
                  onClick={() => setActivePage("Upload Resumes")}
                >
                  Upload Resumes
                </button>
                <button
                  className="btn btn-secondary"
                  onClick={() => openCandidateMatching()}
                >
                  Match Candidates
                </button>
              </div>
            </div>

            {/* Recent Jobs */}
            <div className="card">
              <div className="card-title">
                <span>Recent Job Postings ({stats.recentJobs.length})</span>
                <button
                  className="btn btn-outline btn-sm"
                  onClick={() => setActivePage("Job Descriptions")}
                >
                  Manage All Jobs
                </button>
              </div>

              {stats.recentJobs.length === 0 ? (
                <p style={{ color: "#6b7280", padding: "10px 0" }}>
                  No job descriptions added yet. Click <strong>Add Job Description</strong> to get started.
                </p>
              ) : (
                <div className="table-responsive">
                  <table className="simple-table">
                    <thead>
                      <tr>
                        <th>Job ID</th>
                        <th>Job Title</th>
                        <th>Experience</th>
                        <th>Skills</th>
                        <th>Source</th>
                        <th style={{ textAlign: "right" }}>Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {stats.recentJobs.map((job) => (
                        <tr key={job.id}>
                          <td><strong>#{job.id}</strong></td>
                          <td><strong>{job.title || "Job Description"}</strong></td>
                          <td>
                            {job.min_experience !== null ? `${job.min_experience}` : "0"}
                            {job.max_experience ? ` - ${job.max_experience} yrs` : "+ yrs"}
                          </td>
                          <td>
                            {job.skills && job.skills.length > 0
                              ? job.skills.slice(0, 4).map((s) => s.skill_name).join(", ") +
                                (job.skills.length > 4 ? ` (+${job.skills.length - 4} more)` : "")
                              : "None extracted"}
                          </td>
                          <td><span className="tag tag-gray">{job.source_type}</span></td>
                          <td style={{ textAlign: "right" }}>
                            <button
                              className="btn btn-primary btn-sm"
                              onClick={() => openCandidateMatching(job.id)}
                            >
                              Match Candidates
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        ) : activePage === "Job Descriptions" ? (
          <AddJob onSelectJobForMatching={(jobId) => openCandidateMatching(jobId)} />
        ) : activePage === "Upload Resumes" ? (
          <UploadResumes onProceedToMatching={() => openCandidateMatching()} />
        ) : activePage === "Candidate Matching" ? (
          <CandidateMatching preselectedJobId={selectedJobId} />
        ) : null}
      </main>
    </div>
  );
}

export default App;
