import { useState, useEffect } from "react";
import api from "../services/api";

function UploadResumes({ onProceedToMatching }) {
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [result, setResult] = useState(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [existingResumes, setExistingResumes] = useState([]);
  const [loadingResumes, setLoadingResumes] = useState(false);

  useEffect(() => {
    fetchResumes();
  }, []);

  const fetchResumes = async () => {
    try {
      setLoadingResumes(true);
      const res = await api.get("/resumes");
      setExistingResumes(res.data || []);
    } catch (err) {
      console.warn("Could not load resumes:", err);
    } finally {
      setLoadingResumes(false);
    }
  };

  const handleFilesSelected = (newFiles) => {
    const validFiles = Array.from(newFiles).filter((f) => {
      const ext = f.name.split(".").pop().toLowerCase();
      return ext === "pdf" || ext === "docx";
    });

    if (validFiles.length < newFiles.length) {
      setError("Some files were skipped: Only PDF and DOCX formats are supported.");
    } else {
      setError("");
    }

    setFiles((prev) => {
      const existingNames = new Set(prev.map((f) => f.name));
      const filtered = validFiles.filter((f) => !existingNames.has(f.name));
      return [...prev, ...filtered];
    });

    setResult(null);
    setMessage("");
  };

  const removeFile = (index) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleUploadBatch = async () => {
    if (files.length === 0) {
      setError("Please select at least 1 resume to upload.");
      return;
    }

    const formData = new FormData();
    files.forEach((file) => {
      formData.append("files", file);
    });

    try {
      setLoading(true);
      setError("");
      setMessage("");
      setResult(null);
      setUploadProgress(20);

      const response = await api.post("/resumes/upload", formData, {
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total) {
            const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            setUploadProgress(percent);
          }
        },
      });

      setResult(response.data);
      setMessage(
        `Batch processing complete: Successfully parsed ${response.data.successful} of ${response.data.total_uploaded} resumes.`
      );
      setFiles([]);
      fetchResumes();
    } catch (err) {
      const errorDetail = err.response?.data?.detail;
      setError(
        typeof errorDetail === "string"
          ? errorDetail
          : "Failed to upload and parse resumes. Please check backend connection."
      );
    } finally {
      setLoading(false);
      setUploadProgress(0);
    }
  };

  const handleDeleteResume = async (resumeId) => {
    if (!window.confirm(`Delete candidate resume #${resumeId}?`)) return;
    try {
      await api.delete(`/resumes/${resumeId}`);
      fetchResumes();
    } catch (err) {
      alert("Failed to delete resume: " + (err.response?.data?.detail || err.message));
    }
  };

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Resume Upload & Candidate Extraction</h1>
        <p className="page-desc">
          Upload resumes in batch (supports 10+ resumes in PDF or DOCX format). Candidate information, skills, and experience are extracted automatically.
        </p>
      </div>

      {/* Upload Box */}
      <div className="card">
        <div
          className="file-upload-box"
          onClick={() => document.getElementById("batch-file-input").click()}
        >
          <div style={{ fontWeight: 600, fontSize: "15px", marginBottom: "4px" }}>
            Click to select resumes for batch upload (or drag and drop)
          </div>
          <div style={{ fontSize: "13px", color: "#6b7280" }}>
            Upload 10 or more resumes simultaneously. Supported formats: .pdf, .docx
          </div>

          <input
            id="batch-file-input"
            type="file"
            accept=".pdf,.docx"
            multiple
            style={{ display: "none" }}
            onChange={(e) => handleFilesSelected(e.target.files)}
          />
        </div>

        {/* Selected Files List */}
        {files.length > 0 && (
          <div style={{ marginTop: "16px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
              <span style={{ fontWeight: 600, fontSize: "13px" }}>
                Selected Files ({files.length}):
              </span>
              <button
                className="btn btn-outline btn-sm"
                onClick={() => setFiles([])}
                type="button"
              >
                Clear All
              </button>
            </div>

            <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
              {files.map((file, idx) => (
                <span
                  key={idx}
                  style={{
                    background: "#f3f4f6",
                    border: "1px solid #d1d5db",
                    borderRadius: "4px",
                    padding: "3px 8px",
                    fontSize: "12px",
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "6px",
                  }}
                >
                  {file.name}
                  <button
                    type="button"
                    onClick={() => removeFile(idx)}
                    style={{
                      background: "none",
                      border: "none",
                      color: "#9ca3af",
                      cursor: "pointer",
                      fontWeight: 700,
                    }}
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>

            <div style={{ marginTop: "14px", display: "flex", justifyContent: "flex-end" }}>
              <button
                className="btn btn-primary"
                onClick={handleUploadBatch}
                disabled={loading}
              >
                {loading
                  ? `Processing ${files.length} Resumes in Parallel...`
                  : `Upload & Extract (${files.length} Resumes)`}
              </button>
            </div>
          </div>
        )}

        {/* Status Alerts */}
        {message && <div className="alert alert-success" style={{ marginTop: "14px" }}>{message}</div>}
        {error && <div className="alert alert-error" style={{ marginTop: "14px" }}>{error}</div>}
      </div>

      {/* Fresh Upload Results */}
      {result && (
        <div className="card">
          <div className="card-title">
            <span>Batch Upload Summary</span>
            <button
              className="btn btn-primary btn-sm"
              onClick={() => onProceedToMatching && onProceedToMatching()}
            >
              Proceed to Match Candidates
            </button>
          </div>

          <div style={{ display: "flex", gap: "16px", marginBottom: "14px" }}>
            <div style={{ background: "#f9fafb", padding: "10px 16px", borderRadius: "6px", border: "1px solid #e5e7eb" }}>
              Total Uploaded: <strong>{result.total_uploaded}</strong>
            </div>
            <div style={{ background: "#ecfdf5", padding: "10px 16px", borderRadius: "6px", border: "1px solid #a7f3d0", color: "#065f46" }}>
              Successfully Extracted: <strong>{result.successful}</strong>
            </div>
            {result.failed > 0 && (
              <div style={{ background: "#fef2f2", padding: "10px 16px", borderRadius: "6px", border: "1px solid #fecaca", color: "#991b1b" }}>
                Failed: <strong>{result.failed}</strong>
              </div>
            )}
            {result.duplicates_detected > 0 && (
              <div style={{ background: "#fef3c7", padding: "10px 16px", borderRadius: "6px", border: "1px solid #fcd34d", color: "#92400e" }}>
                Duplicates Updated: <strong>{result.duplicates_detected}</strong>
              </div>
            )}
          </div>

          {result.duplicates && result.duplicates.length > 0 && (
            <div style={{ marginTop: "10px", padding: "12px", background: "#fffbeb", borderRadius: "6px", border: "1px solid #fcd34d", fontSize: "13px" }}>
              <strong>Duplicate resumes detected:</strong>
              <ul style={{ margin: "6px 0 0 20px", padding: 0 }}>
                {result.duplicates.map((d, i) => (
                  <li key={i} style={{ color: "#92400e", marginBottom: "3px" }}>
                    {d.filename} — {d.reason === "exact_file" ? "Exact same file already uploaded" : d.reason === "email_match" ? "Same candidate email found in database" : "Same candidate detected"}
                    {d.resume_id && <span> (Resume #{d.resume_id})</span>}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Resumes in Database Table */}
      <div className="card">
        <div className="card-title">
          <span>Resumes Stored in Database ({existingResumes.length})</span>
          <div style={{ display: "flex", gap: "8px" }}>
            <button className="btn btn-outline btn-sm" onClick={fetchResumes} type="button">
              Refresh
            </button>
            {existingResumes.length > 0 && (
              <button
                className="btn btn-primary btn-sm"
                onClick={() => onProceedToMatching && onProceedToMatching()}
              >
                Match Candidates
              </button>
            )}
          </div>
        </div>

        {loadingResumes ? (
          <p style={{ color: "#6b7280" }}>Loading candidate resumes...</p>
        ) : existingResumes.length === 0 ? (
          <p style={{ color: "#6b7280" }}>No candidate resumes uploaded yet.</p>
        ) : (
          <div className="table-responsive">
            <table className="simple-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Candidate Name</th>
                  <th>Email</th>
                  <th>Phone</th>
                  <th>Experience</th>
                  <th>Top Skills</th>
                  <th>Format</th>
                  <th>Date</th>
                  <th style={{ textAlign: "right" }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {existingResumes.map((res) => (
                  <tr key={res.id}>
                    <td><strong>#{res.id}</strong></td>
                    <td>
                      <strong>{res.full_name || res.original_filename || "Candidate"}</strong>
                    </td>
                    <td>{res.email || "—"}</td>
                    <td>{res.phone || "—"}</td>
                    <td>
                      {res.work_experience !== null ? `${res.work_experience} yrs` : "—"}
                    </td>
                    <td>
                      {res.technical_skills && res.technical_skills.length > 0
                        ? res.technical_skills.slice(0, 5).join(", ") +
                          (res.technical_skills.length > 5
                            ? ` (+${res.technical_skills.length - 5} more)`
                            : "")
                        : "—"}
                    </td>
                    <td><span className="tag tag-gray">{res.file_type}</span></td>
                    <td style={{ color: "#6b7280", fontSize: "12px" }}>
                      {res.created_at ? new Date(res.created_at).toLocaleDateString() : "--"}
                    </td>
                    <td style={{ textAlign: "right" }}>
                      <button
                        className="btn btn-danger btn-sm"
                        onClick={() => handleDeleteResume(res.id)}
                      >
                        Delete
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
  );
}

export default UploadResumes;
