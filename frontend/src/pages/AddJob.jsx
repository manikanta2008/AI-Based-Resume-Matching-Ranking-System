import { useState, useEffect } from "react";
import api from "../services/api";

const SAMPLE_JD = `Job Title: Senior Full Stack Developer (Java & React)
Location: Remote / Hybrid
Experience Required: 4 - 7 years
Education: Bachelor's or Master's degree in Computer Science, Engineering or related field.

About the Role:
We are looking for an experienced Senior Full Stack Developer to build robust, scalable cloud applications. You will collaborate with cross-functional teams to design high-throughput REST APIs and rich frontend web experiences.

Key Responsibilities:
- Design, build, and maintain scalable backend services using Java and Spring Boot.
- Develop interactive, responsive user interfaces using React, TypeScript, and modern CSS.
- Optimize complex database queries and data models in PostgreSQL and SQL.
- Implement containerized deployments using Docker and Kubernetes on AWS cloud infrastructure.
- Write high-quality automated unit and integration tests to ensure system reliability.

Required Skills:
- Java, Spring Boot, Microservices
- React, JavaScript / TypeScript, HTML/CSS
- PostgreSQL, SQL, Database Design
- REST API, Git, Docker

Preferred Skills:
- AWS, Kubernetes, CI/CD pipelines
- Kafka, Redis caching, Python`;

function AddJob({ onSelectJobForMatching }) {
  const [activeTab, setActiveTab] = useState("paste"); // "paste" | "upload"
  const [jdText, setJdText] = useState("");
  const [jdFile, setJdFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [preview, setPreview] = useState(null);
  const [extractedSourceText, setExtractedSourceText] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [savedJobId, setSavedJobId] = useState(null);
  const [savedJobs, setSavedJobs] = useState([]);
  const [loadingJobs, setLoadingJobs] = useState(false);

  useEffect(() => {
    fetchJobs();
  }, []);

  const fetchJobs = async () => {
    try {
      setLoadingJobs(true);
      const res = await api.get("/jobs");
      setSavedJobs(res.data || []);
    } catch (err) {
      console.warn("Could not load jobs:", err);
    } finally {
      setLoadingJobs(false);
    }
  };

  const handleLoadSample = () => {
    setJdText(SAMPLE_JD);
    setMessage("");
    setError("");
  };

  const handleFileInputChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      const ext = file.name.split(".").pop().toLowerCase();
      if (ext !== "pdf" && ext !== "docx") {
        setError("Please select a PDF or DOCX file.");
        return;
      }
      setJdFile(file);
      setError("");
      setMessage(`Selected file: ${file.name}`);
    }
  };

  const handleExtractFromText = async () => {
    if (!jdText.trim() || jdText.trim().length < 20) {
      setError("Please paste a comprehensive Job Description (at least 20 characters).");
      return;
    }

    try {
      setLoading(true);
      setError("");
      setMessage("");
      setPreview(null);
      setSavedJobId(null);

      const response = await api.post("/jobs/preview", {
        jd_text: jdText,
        source_type: "text",
        use_gemini: true,
      });

      setPreview(response.data.data);
      setExtractedSourceText(jdText);
      setMessage("Job description analyzed and requirements extracted successfully!");
    } catch (err) {
      setError(
        err.response?.data?.detail || "Failed to extract job details. Please try again."
      );
    } finally {
      setLoading(false);
    }
  };

  const handleExtractFromFile = async () => {
    if (!jdFile) {
      setError("Please select a PDF or DOCX Job Description document.");
      return;
    }

    const formData = new FormData();
    formData.append("file", jdFile);
    formData.append("use_gemini", "true");

    try {
      setLoading(true);
      setError("");
      setMessage("");
      setPreview(null);
      setSavedJobId(null);

      const response = await api.post("/jobs/upload-file", formData);
      setPreview(response.data.data);
      setExtractedSourceText(response.data.extracted_text || "");
      setMessage(`Successfully extracted requirements from ${jdFile.name}!`);
    } catch (err) {
      setError(
        err.response?.data?.detail || "Failed to process uploaded file."
      );
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmAndSave = async () => {
    if (!preview) {
      setError("No extracted job details to save. Please extract first.");
      return;
    }

    try {
      setLoading(true);
      setError("");

      const payload = {
        title: preview.title || "Job Description",
        min_experience: preview.min_experience,
        max_experience: preview.max_experience,
        education: preview.education || [],
        responsibilities: preview.responsibilities || [],
        keywords: preview.keywords || [],
        skills: preview.skills || [],
        original_jd: extractedSourceText || jdText || "Job Description",
        source_type: activeTab === "upload" && jdFile ? (jdFile.name.endsWith(".docx") ? "docx" : "pdf") : "text",
      };

      const response = await api.post("/jobs/confirm", payload);
      setSavedJobId(response.data.id);
      if (response.data.duplicate_detected) {
        setMessage(`⚠ ${response.data.message || "This job description already exists. Updated the existing record."}`);
      } else {
        setMessage(`Job Description successfully confirmed and saved! (Job ID: #${response.data.id})`);
      }
      fetchJobs();
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to save job description.");
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteJob = async (jobId) => {
    if (!window.confirm(`Are you sure you want to delete Job #${jobId}?`)) return;
    try {
      await api.delete(`/jobs/${jobId}`);
      fetchJobs();
    } catch (err) {
      alert("Failed to delete job: " + (err.response?.data?.detail || err.message));
    }
  };

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Job Descriptions</h1>
        <p className="page-desc">
          Paste or upload a Job Description to extract key requirements, experience constraints, and required vs. preferred skills.
        </p>
      </div>

      {/* Tabs */}
      <div className="tabs">
        <button
          className={`tab-btn ${activeTab === "paste" ? "active" : ""}`}
          onClick={() => { setActiveTab("paste"); setMessage(""); setError(""); }}
        >
          Paste Text
        </button>
        <button
          className={`tab-btn ${activeTab === "upload" ? "active" : ""}`}
          onClick={() => { setActiveTab("upload"); setMessage(""); setError(""); }}
        >
          Upload Document (.pdf, .docx)
        </button>
      </div>

      {/* Input Form Card */}
      <div className="card">
        {activeTab === "paste" ? (
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
              <label className="form-label" style={{ marginBottom: 0 }}>
                Job Description Text
              </label>
              <button className="btn btn-outline btn-sm" onClick={handleLoadSample} type="button">
                Load Sample JD
              </button>
            </div>

            <textarea
              className="form-textarea"
              rows={8}
              placeholder="Paste the complete job description text here..."
              value={jdText}
              onChange={(e) => setJdText(e.target.value)}
            />

            <div style={{ marginTop: "12px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: "12px", color: "#6b7280" }}>
                {jdText.length} characters
              </span>
              <button
                className="btn btn-primary"
                onClick={handleExtractFromText}
                disabled={loading || !jdText.trim()}
              >
                {loading ? "Extracting..." : "Extract Requirements"}
              </button>
            </div>
          </div>
        ) : (
          <div>
            <div className="file-upload-box" onClick={() => document.getElementById("jd-file-input").click()}>
              <div style={{ fontWeight: 600, fontSize: "15px", marginBottom: "4px" }}>
                Click to select Job Description file
              </div>
              <div style={{ fontSize: "13px", color: "#6b7280" }}>
                Supported formats: PDF (.pdf) or Word document (.docx)
              </div>
              {jdFile && (
                <div style={{ marginTop: "12px", fontWeight: 600, color: "#2563eb" }}>
                  Selected: {jdFile.name} ({(jdFile.size / 1024).toFixed(1)} KB)
                </div>
              )}
              <input
                id="jd-file-input"
                type="file"
                accept=".pdf,.docx"
                style={{ display: "none" }}
                onChange={handleFileInputChange}
              />
            </div>

            <div style={{ marginTop: "14px", display: "flex", justifyContent: "flex-end" }}>
              <button
                className="btn btn-primary"
                onClick={handleExtractFromFile}
                disabled={loading || !jdFile}
              >
                {loading ? "Processing..." : "Extract Requirements"}
              </button>
            </div>
          </div>
        )}

        {/* Feedback alerts */}
        {message && <div className="alert alert-success" style={{ marginTop: "14px" }}>{message}</div>}
        {error && <div className="alert alert-error" style={{ marginTop: "14px" }}>{error}</div>}
      </div>

      {/* Extracted Requirements Preview */}
      {preview && (
        <div className="card">
          <div className="card-title">
            <span>Extracted Job Requirements Preview</span>
            {savedJobId && <span className="tag tag-green">Saved as Job #{savedJobId}</span>}
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: "16px", marginBottom: "16px" }}>
            <div style={{ background: "#f9fafb", padding: "14px", borderRadius: "6px", border: "1px solid #e5e7eb" }}>
              <div style={{ fontSize: "12px", color: "#6b7280", fontWeight: 600 }}>JOB TITLE</div>
              <div style={{ fontSize: "16px", fontWeight: 700, marginTop: "4px" }}>
                {preview.title || "Untitled Role"}
              </div>
              <div style={{ marginTop: "8px", fontSize: "13px" }}>
                <strong>Experience:</strong> {preview.min_experience !== null ? `${preview.min_experience}` : "0"}
                {preview.max_experience ? ` - ${preview.max_experience} years` : "+ years"}
              </div>
              {preview.education && preview.education.length > 0 && (
                <div style={{ marginTop: "4px", fontSize: "13px" }}>
                  <strong>Education:</strong> {preview.education.join(", ")}
                </div>
              )}
            </div>

            <div style={{ background: "#f9fafb", padding: "14px", borderRadius: "6px", border: "1px solid #e5e7eb" }}>
              <div style={{ fontSize: "12px", color: "#6b7280", fontWeight: 600, marginBottom: "6px" }}>
                REQUIRED SKILLS ({preview.skills?.filter(s => s.skill_type === "required").length || 0})
              </div>
              <div>
                {preview.skills?.filter(s => s.skill_type === "required").map((skill, i) => (
                  <span key={i} className="tag tag-blue">{skill.skill_name}</span>
                ))}
                {(!preview.skills || preview.skills.filter(s => s.skill_type === "required").length === 0) && (
                  <span style={{ fontSize: "12px", color: "#9ca3af" }}>None identified</span>
                )}
              </div>

              <div style={{ fontSize: "12px", color: "#6b7280", fontWeight: 600, marginTop: "12px", marginBottom: "6px" }}>
                PREFERRED SKILLS ({preview.skills?.filter(s => s.skill_type === "preferred").length || 0})
              </div>
              <div>
                {preview.skills?.filter(s => s.skill_type === "preferred").map((skill, i) => (
                  <span key={i} className="tag tag-gray">{skill.skill_name}</span>
                ))}
                {(!preview.skills || preview.skills.filter(s => s.skill_type === "preferred").length === 0) && (
                  <span style={{ fontSize: "12px", color: "#9ca3af" }}>None identified</span>
                )}
              </div>
            </div>
          </div>

          <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px" }}>
            {!savedJobId ? (
              <button
                className="btn btn-primary"
                onClick={handleConfirmAndSave}
                disabled={loading}
              >
                {loading ? "Saving..." : "Confirm & Save Job Description"}
              </button>
            ) : (
              <button
                className="btn btn-primary"
                onClick={() => onSelectJobForMatching && onSelectJobForMatching(savedJobId)}
              >
                Proceed to Match Candidates
              </button>
            )}
          </div>
        </div>
      )}

      {/* Saved Jobs List */}
      <div className="card">
        <div className="card-title">
          <span>Saved Job Descriptions ({savedJobs.length})</span>
          <button className="btn btn-outline btn-sm" onClick={fetchJobs} type="button">
            Refresh
          </button>
        </div>

        {loadingJobs ? (
          <p style={{ color: "#6b7280" }}>Loading saved jobs...</p>
        ) : savedJobs.length === 0 ? (
          <p style={{ color: "#6b7280" }}>No saved jobs yet. Add one above.</p>
        ) : (
          <div className="table-responsive">
            <table className="simple-table">
              <thead>
                <tr>
                  <th>Job ID</th>
                  <th>Title</th>
                  <th>Experience</th>
                  <th>Skills Extracted</th>
                  <th>Source</th>
                  <th>Date</th>
                  <th style={{ textAlign: "right" }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {savedJobs.map((job) => (
                  <tr key={job.id}>
                    <td><strong>#{job.id}</strong></td>
                    <td><strong>{job.title || "Job Description"}</strong></td>
                    <td>
                      {job.min_experience !== null ? `${job.min_experience}` : "0"}
                      {job.max_experience ? ` - ${job.max_experience} yrs` : "+ yrs"}
                    </td>
                    <td>
                      {job.skills && job.skills.length > 0
                        ? job.skills.slice(0, 5).map((s) => s.skill_name).join(", ") +
                          (job.skills.length > 5 ? ` (+${job.skills.length - 5} more)` : "")
                        : "—"}
                    </td>
                    <td><span className="tag tag-gray">{job.source_type}</span></td>
                    <td style={{ color: "#6b7280", fontSize: "12px" }}>
                      {job.created_at ? new Date(job.created_at).toLocaleDateString() : "--"}
                    </td>
                    <td style={{ textAlign: "right" }}>
                      <div style={{ display: "inline-flex", gap: "6px" }}>
                        <button
                          className="btn btn-primary btn-sm"
                          onClick={() => onSelectJobForMatching && onSelectJobForMatching(job.id)}
                        >
                          Match
                        </button>
                        <button
                          className="btn btn-danger"
                          onClick={() => handleDeleteJob(job.id)}
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

export default AddJob;
