import { useState, useEffect } from "react";
import api from "../services/api";

function CandidateMatching({ preselectedJobId }) {
  const [jobs, setJobs] = useState([]);
  const [selectedJobId, setSelectedJobId] = useState(preselectedJobId ? String(preselectedJobId) : "");
  const [resumes, setResumes] = useState([]);
  const [selectedResumeIds, setSelectedResumeIds] = useState([]);

  const [loading, setLoading] = useState(false);
  const [loadingInitial, setLoadingInitial] = useState(true);
  const [results, setResults] = useState(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const [searchQuery, setSearchQuery] = useState("");
  const [minScoreFilter, setMinScoreFilter] = useState(0);

  // Candidate detail modal
  const [activeCandidate, setActiveCandidate] = useState(null);

  useEffect(() => {
    loadJobsAndResumes();
  }, []);

  useEffect(() => {
    if (preselectedJobId) {
      setSelectedJobId(String(preselectedJobId));
      fetchExistingRankings(Number(preselectedJobId));
    }
  }, [preselectedJobId]);

  const loadJobsAndResumes = async () => {
    try {
      setLoadingInitial(true);
      const [jobsRes, resumesRes] = await Promise.all([
        api.get("/jobs").catch(() => ({ data: [] })),
        api.get("/resumes").catch(() => ({ data: [] })),
      ]);

      const jobsData = jobsRes.data || [];
      const resumesData = resumesRes.data || [];

      setJobs(jobsData);
      setResumes(resumesData);

      if (preselectedJobId) {
        setSelectedJobId(String(preselectedJobId));
        fetchExistingRankings(Number(preselectedJobId));
      } else if (jobsData.length > 0) {
        const firstJobId = jobsData[0].id;
        setSelectedJobId(String(firstJobId));
        fetchExistingRankings(firstJobId);
      }

      if (resumesData.length > 0) {
        setSelectedResumeIds(resumesData.map((r) => r.id));
      }
    } finally {
      setLoadingInitial(false);
    }
  };

  const fetchExistingRankings = async (jobId) => {
    if (!jobId) return;
    try {
      const res = await api.get(`/resumes/rankings/${jobId}`);
      if (res.data?.ranked_candidates && res.data.ranked_candidates.length > 0) {
        setResults({
          job_id: jobId,
          job_title: res.data.job_title,
          total_resumes: res.data.total_candidates,
          successful: res.data.total_candidates,
          failed: 0,
          ranked_candidates: res.data.ranked_candidates,
        });
      }
    } catch {
      // No ranking yet
    }
  };

  const handleJobChange = (jobId) => {
    setSelectedJobId(jobId);
    setResults(null);
    setMessage("");
    setError("");
    if (jobId) {
      fetchExistingRankings(Number(jobId));
    }
  };

  const toggleSelectAllResumes = () => {
    if (selectedResumeIds.length === resumes.length) {
      setSelectedResumeIds([]);
    } else {
      setSelectedResumeIds(resumes.map((r) => r.id));
    }
  };

  const handleRunMatching = async () => {
    const numJobId = Number(selectedJobId);
    if (!numJobId || isNaN(numJobId)) {
      setError("Please select a Job Description first.");
      return;
    }

    if (selectedResumeIds.length === 0) {
      setError("Please select at least 1 resume to match.");
      return;
    }

    try {
      setLoading(true);
      setError("");
      setMessage("");

      const response = await api.post("/resumes/match-batch", {
        job_id: numJobId,
        resume_ids: selectedResumeIds,
      });

      setResults(response.data);
      setMessage(
        `Matching complete: Evaluated ${response.data.successful} candidate resumes against Job #${numJobId}!`
      );
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(
        typeof detail === "string"
          ? detail
          : "Candidate matching failed. Please check backend connection."
      );
    } finally {
      setLoading(false);
    }
  };

  const filteredCandidates = (results?.ranked_candidates || []).filter((cand) => {
    const score = Number(cand.overall_score || 0);
    if (score < minScoreFilter) return false;

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const name = (cand.candidate_name || "").toLowerCase();
      const skills = (cand.matched_skills || []).join(" ").toLowerCase();
      return name.includes(q) || skills.includes(q);
    }

    return true;
  });

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Candidate Matching & Ranking Dashboard</h1>
        <p className="page-desc">
          Compare candidate resumes against job descriptions, calculate match percentages, view ranking, and examine individual candidate-level analyses.
        </p>
      </div>

      {/* Configuration Card */}
      <div className="card">
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "16px", alignItems: "flex-end" }}>
          {/* Job Select */}
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label className="form-label">Select Job Description:</label>
            <select
              className="form-select"
              value={selectedJobId}
              onChange={(e) => handleJobChange(e.target.value)}
              disabled={loadingInitial || jobs.length === 0}
            >
              <option value="">-- Choose a Job Description --</option>
              {jobs.map((job) => (
                <option key={job.id} value={job.id}>
                  #{job.id} - {job.title || "Job Description"} ({job.skills?.length || 0} skills)
                </option>
              ))}
            </select>
          </div>

          {/* Resumes Select Summary */}
          <div className="form-group" style={{ marginBottom: 0 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
              <label className="form-label" style={{ marginBottom: 0 }}>Resumes to Match:</label>
              <button
                type="button"
                className="btn btn-outline btn-sm"
                onClick={toggleSelectAllResumes}
              >
                {selectedResumeIds.length === resumes.length ? "Deselect All" : "Select All"}
              </button>
            </div>
            <div style={{ fontSize: "13px", color: "#4b5563", padding: "8px 0" }}>
              <strong>{selectedResumeIds.length}</strong> of <strong>{resumes.length}</strong> candidate resumes selected
            </div>
          </div>

          {/* Action Button */}
          <div>
            <button
              className="btn btn-primary"
              style={{ width: "100%", padding: "10px" }}
              onClick={handleRunMatching}
              disabled={loading || !selectedJobId || selectedResumeIds.length === 0}
            >
              {loading ? "Evaluating Resumes in Parallel..." : "Run AI Resume Matching"}
            </button>
          </div>
        </div>

        {/* Feedback alerts */}
        {message && <div className="alert alert-success" style={{ marginTop: "14px" }}>{message}</div>}
        {error && <div className="alert alert-error" style={{ marginTop: "14px" }}>{error}</div>}
      </div>

      {/* Candidate Ranking Dashboard Table */}
      <div className="card">
        <div className="card-title">
          <span>Candidate Ranking Dashboard</span>
          {results && (
            <span style={{ fontSize: "13px", color: "#6b7280" }}>
              {filteredCandidates.length} Candidates Ranked
            </span>
          )}
        </div>

        {/* Search & Filter */}
        <div style={{ display: "flex", gap: "12px", alignItems: "center", marginBottom: "14px", flexWrap: "wrap" }}>
          <input
            type="text"
            className="form-input"
            style={{ maxWidth: "300px" }}
            placeholder="Search candidate name or skill..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />

          <select
            className="form-select"
            style={{ width: "140px" }}
            value={minScoreFilter}
            onChange={(e) => setMinScoreFilter(Number(e.target.value))}
          >
            <option value={0}>All Scores</option>
            <option value={50}>50%+ Match</option>
            <option value={70}>70%+ Match</option>
            <option value={80}>80%+ Match</option>
          </select>
        </div>

        {!results ? (
          <p style={{ color: "#6b7280", padding: "20px 0", textAlign: "center" }}>
            Select a Job Description and click <strong>Run AI Resume Matching</strong> to generate the candidate ranking table.
          </p>
        ) : filteredCandidates.length === 0 ? (
          <p style={{ color: "#6b7280", padding: "20px 0", textAlign: "center" }}>
            No candidates matched the current search filters.
          </p>
        ) : (
          <div className="table-responsive">
            <table className="simple-table">
              <thead>
                <tr>
                  <th style={{ width: "60px" }}>Rank</th>
                  <th>Candidate</th>
                  <th>Experience</th>
                  <th>Match %</th>
                  <th>Matched Skills</th>
                  <th>Missing Skills</th>
                  <th style={{ textAlign: "right" }}>Analysis</th>
                </tr>
              </thead>
              <tbody>
                {filteredCandidates.map((cand, idx) => {
                  const score = Math.round(cand.overall_score || 0);
                  const scoreClass = score >= 80 ? "score-high" : score >= 65 ? "score-medium" : "score-low";

                  return (
                    <tr
                      key={cand.resume_id || idx}
                      className="clickable"
                      onClick={() => setActiveCandidate(cand)}
                    >
                      <td><strong>#{cand.rank || idx + 1}</strong></td>
                      <td>
                        <strong>{cand.candidate_name}</strong>
                        {cand.email && <div style={{ fontSize: "11px", color: "#6b7280" }}>{cand.email}</div>}
                      </td>
                      <td>
                        {cand.experience_years !== null ? `${cand.experience_years} years` : "—"}
                      </td>
                      <td>
                        <span className={`score-badge ${scoreClass}`}>{score}%</span>
                      </td>
                      <td>
                        {cand.matched_skills && cand.matched_skills.length > 0 ? (
                          cand.matched_skills.slice(0, 5).map((s, i) => (
                            <span key={i} className="tag tag-green">{s}</span>
                          ))
                        ) : (
                          <span style={{ color: "#9ca3af" }}>None</span>
                        )}
                        {cand.matched_skills?.length > 5 && (
                          <span style={{ fontSize: "11px", color: "#6b7280" }}>
                            +{cand.matched_skills.length - 5}
                          </span>
                        )}
                      </td>
                      <td>
                        {cand.missing_skills && cand.missing_skills.length > 0 ? (
                          cand.missing_skills.slice(0, 3).map((s, i) => (
                            <span key={i} className="tag tag-red">{s}</span>
                          ))
                        ) : (
                          <span style={{ color: "#16a34a", fontSize: "12px" }}>None</span>
                        )}
                      </td>
                      <td style={{ textAlign: "right" }}>
                        <button
                          className="btn btn-outline btn-sm"
                          onClick={(e) => {
                            e.stopPropagation();
                            setActiveCandidate(cand);
                          }}
                        >
                          View Details
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Candidate-Level Analysis Modal */}
      {activeCandidate && (
        <div className="modal-backdrop" onClick={() => setActiveCandidate(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div>
                <h3 className="modal-title">{activeCandidate.candidate_name}</h3>
                <div style={{ fontSize: "12px", color: "#6b7280", marginTop: "2px" }}>
                  {activeCandidate.email || "No email"} | {activeCandidate.phone || "No phone"}
                </div>
              </div>
              <button className="close-btn" onClick={() => setActiveCandidate(null)}>×</button>
            </div>

            {/* Overall Matching Score */}
            <div className="modal-section" style={{ background: "#f0f7ff", padding: "16px", borderRadius: "8px", border: "1px solid #bfdbfe" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <div className="modal-section-title" style={{ marginBottom: "2px" }}>Overall Matching Score</div>
                  <div style={{ fontSize: "12px", color: "#6b7280" }}>
                    Weighted: Required Skills (40%) + Experience (20%) + Preferred Skills (15%) + Semantic (15%) + Education (10%)
                  </div>
                </div>
                <div style={{ fontSize: "32px", fontWeight: 700, color: "#2563eb" }}>
                  {Math.round(activeCandidate.overall_score || 0)}%
                </div>
              </div>
            </div>

            {/* Score Breakdown Bars */}
            <div className="modal-section">
              <div className="modal-section-title">Score Breakdown by Component</div>
              {[
                { label: "Required Skills", key: "required_skills_score", weight: 40, color: "#2563eb" },
                { label: "Experience", key: "experience_score", weight: 20, color: "#7c3aed" },
                { label: "Preferred Skills", key: "preferred_skills_score", weight: 15, color: "#0891b2" },
                { label: "Semantic Relevance", key: "semantic_score", weight: 15, color: "#059669" },
                { label: "Education", key: "education_score", weight: 10, color: "#d97706" },
              ].map((item) => {
                const score = Math.round(activeCandidate[item.key] || 0);
                return (
                  <div key={item.key} style={{ marginBottom: "10px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", marginBottom: "3px" }}>
                      <span style={{ fontWeight: 600, color: "#374151" }}>
                        {item.label} <span style={{ fontWeight: 400, color: "#9ca3af" }}>({item.weight}% weight)</span>
                      </span>
                      <span style={{ fontWeight: 700, color: item.color }}>{score}%</span>
                    </div>
                    <div style={{ background: "#f3f4f6", borderRadius: "4px", height: "8px", overflow: "hidden" }}>
                      <div style={{ width: `${score}%`, height: "100%", background: item.color, borderRadius: "4px", transition: "width 0.3s" }} />
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Required Skills */}
            <div className="modal-section">
              <div className="modal-section-title">Required Skills Analysis</div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
                <div style={{ background: "#ecfdf5", padding: "12px", borderRadius: "6px", border: "1px solid #a7f3d0" }}>
                  <div style={{ fontWeight: 600, color: "#065f46", fontSize: "12px", marginBottom: "6px" }}>
                    Matched ({activeCandidate.matched_required_skills?.length || 0})
                  </div>
                  {activeCandidate.matched_required_skills?.length > 0 ? (
                    <div>{activeCandidate.matched_required_skills.map((s, i) => (<span key={i} className="tag tag-green">{s}</span>))}</div>
                  ) : (
                    <div style={{ fontSize: "12px", color: "#6b7280" }}>No matching required skills</div>
                  )}
                </div>
                <div style={{ background: "#fef2f2", padding: "12px", borderRadius: "6px", border: "1px solid #fecaca" }}>
                  <div style={{ fontWeight: 600, color: "#991b1b", fontSize: "12px", marginBottom: "6px" }}>
                    Missing ({activeCandidate.missing_required_skills?.length || 0})
                  </div>
                  {activeCandidate.missing_required_skills?.length > 0 ? (
                    <div>{activeCandidate.missing_required_skills.map((s, i) => (<span key={i} className="tag tag-red">{s}</span>))}</div>
                  ) : (
                    <div style={{ fontSize: "12px", color: "#16a34a" }}>All required skills covered!</div>
                  )}
                </div>
              </div>
            </div>

            {/* Preferred Skills */}
            <div className="modal-section">
              <div className="modal-section-title">Preferred Skills Analysis</div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
                <div style={{ background: "#eff6ff", padding: "12px", borderRadius: "6px", border: "1px solid #bfdbfe" }}>
                  <div style={{ fontWeight: 600, color: "#1e40af", fontSize: "12px", marginBottom: "6px" }}>
                    Matched ({activeCandidate.matched_preferred_skills?.length || 0})
                  </div>
                  {activeCandidate.matched_preferred_skills?.length > 0 ? (
                    <div>{activeCandidate.matched_preferred_skills.map((s, i) => (<span key={i} className="tag tag-blue">{s}</span>))}</div>
                  ) : (
                    <div style={{ fontSize: "12px", color: "#6b7280" }}>No matching preferred skills</div>
                  )}
                </div>
                <div style={{ background: "#f9fafb", padding: "12px", borderRadius: "6px", border: "1px solid #e5e7eb" }}>
                  <div style={{ fontWeight: 600, color: "#6b7280", fontSize: "12px", marginBottom: "6px" }}>
                    Missing ({activeCandidate.missing_preferred_skills?.length || 0})
                  </div>
                  {activeCandidate.missing_preferred_skills?.length > 0 ? (
                    <div>{activeCandidate.missing_preferred_skills.map((s, i) => (<span key={i} className="tag tag-gray">{s}</span>))}</div>
                  ) : (
                    <div style={{ fontSize: "12px", color: "#059669" }}>All preferred skills covered!</div>
                  )}
                </div>
              </div>
            </div>

            {/* Experience Analysis */}
            <div className="modal-section">
              <div className="modal-section-title">Experience Analysis</div>
              <div style={{ background: "#f9fafb", padding: "12px", borderRadius: "6px", border: "1px solid #e5e7eb", fontSize: "13px" }}>
                <div><strong>Candidate Experience:</strong> {activeCandidate.experience_years != null ? `${activeCandidate.experience_years} years` : "Not specified"}</div>
                {activeCandidate.experience_analysis && (
                  <div style={{ marginTop: "6px", color: "#4b5563" }}>
                    {typeof activeCandidate.experience_analysis === "string" ? activeCandidate.experience_analysis : activeCandidate.experience_analysis.analysis || JSON.stringify(activeCandidate.experience_analysis)}
                  </div>
                )}
              </div>
            </div>

            {/* Education Analysis */}
            <div className="modal-section">
              <div className="modal-section-title">Education Analysis</div>
              <div style={{ background: "#f9fafb", padding: "12px", borderRadius: "6px", border: "1px solid #e5e7eb", fontSize: "13px" }}>
                {activeCandidate.education_analysis ? (
                  <div style={{ color: "#4b5563" }}>
                    {typeof activeCandidate.education_analysis === "string" ? activeCandidate.education_analysis : activeCandidate.education_analysis.analysis || JSON.stringify(activeCandidate.education_analysis)}
                  </div>
                ) : (<div style={{ color: "#6b7280" }}>Education analysis not available</div>)}
              </div>
            </div>

            {/* Semantic Analysis */}
            <div className="modal-section">
              <div className="modal-section-title">Semantic Relevance Analysis</div>
              <div style={{ background: "#f9fafb", padding: "12px", borderRadius: "6px", border: "1px solid #e5e7eb", fontSize: "13px" }}>
                {activeCandidate.semantic_analysis ? (
                  <div style={{ color: "#4b5563" }}>
                    {typeof activeCandidate.semantic_analysis === "string" ? activeCandidate.semantic_analysis : activeCandidate.semantic_analysis.analysis || JSON.stringify(activeCandidate.semantic_analysis)}
                  </div>
                ) : (<div style={{ color: "#6b7280" }}>Semantic analysis not available</div>)}
              </div>
            </div>

            {/* Why This Match Score */}
            <div className="modal-section">
              <div className="modal-section-title" style={{ color: "#2563eb" }}>Why This Match Score?</div>
              <div style={{ background: "#f0f7ff", padding: "14px", borderRadius: "6px", border: "1px solid #bfdbfe", fontSize: "13px", lineHeight: 1.7, color: "#1e3a5f" }}>
                {activeCandidate.ai_explanation || "Score calculated using weighted combination of skill coverage, experience alignment, education match, and semantic relevance."}
              </div>
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end" }}>
              <button className="btn btn-secondary" onClick={() => setActiveCandidate(null)}>Close</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default CandidateMatching;
