import os
import time
import tempfile

import streamlit as st

from jd_scraper.scrape_jd import scrape_job_description
from jd_parser.extract_requirements import extract_skills_and_keywords
from resume_parser.parse_resume import parse_resume
from ai_engine.rewrite_resume import (
    generate_tailored_resume,
    build_content_inventory,
    get_known_companies_and_projects,
    verify_resume_format,
)
from ai_engine.validate_resume import validate_resume_content
from ai_engine.cover_letter import generate_cover_letter
from generator.generate_latex import generate_resume_latex, parse_resume_text
from generator.cover_letter_latex import generate_cover_letter_latex
from employer.database import (
    add_resume,
    list_resumes,
    delete_resume,
    get_resume_count,
)
from employer.shortlist import shortlist

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Resume AI Platform",
    page_icon="🧠",
    layout="wide",
)

# ── Session state defaults ────────────────────────────────────────────────────
for key, default in {
    "pdf_bytes":         None,
    "verify_result":     None,
    "tailored_text":     None,
    "candidate_name":    "",
    "cl_bytes":          None,
    "jd_info_cache":     {},
    "linkedin_url_cache":"",
    "shortlist_results": [],
    "shortlist_run":     False,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ── Top-level tabs ────────────────────────────────────────────────────────────
tab_candidate, tab_employer = st.tabs(["👤 Candidate Portal", "🏢 Employer Portal"])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — CANDIDATE PORTAL  (all original logic, unchanged)
# ══════════════════════════════════════════════════════════════════════════════

with tab_candidate:
    st.title("Resume Tailor AI")
    st.markdown("Tailor your resume and generate a cover letter for any job application.")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.header("Job Description")
        jd_url = st.text_input(
            "Enter Job URL",
            placeholder="https://example.com/job-posting",
            key="candidate_jd_url",
        )

        st.header("Upload Base Resume")
        uploaded_file = st.file_uploader(
            "Upload your resume (PDF)",
            type=["pdf"],
            key="candidate_resume_upload",
        )

        linkedin_url = st.text_input(
            "LinkedIn Profile URL",
            placeholder="https://www.linkedin.com/in/your-profile",
            key="candidate_linkedin",
        )

        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            generate_btn = st.button(
                "📄 Generate Resume",
                use_container_width=True,
                key="candidate_gen_resume",
            )
        with btn_col2:
            generate_cl_btn_top = st.button(
                "✉️ Generate Cover Letter",
                use_container_width=True,
                key="candidate_gen_cl",
                disabled=not bool(st.session_state.get("tailored_text")),
            )

    with col2:
        st.header("Generated Resume")

        if generate_btn:
            if not jd_url:
                st.error("Please enter a job URL")
            elif not uploaded_file:
                st.error("Please upload your resume")
            else:
                with st.spinner("Processing..."):
                    try:
                        st.info("Scraping job description...")
                        jd_text = scrape_job_description(jd_url)

                        st.info("Extracting skills and keywords from JD...")
                        jd_info = extract_skills_and_keywords(jd_text)
                        st.session_state["jd_info_cache"] = jd_info

                        st.info("Parsing your resume...")
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                            tmp.write(uploaded_file.getvalue())
                            tmp_path = tmp.name
                        resume_text = parse_resume(tmp_path)
                        os.unlink(tmp_path)

                        if linkedin_url and linkedin_url.strip():
                            resume_text = f"LinkedIn: {linkedin_url.strip()}\n" + resume_text
                        st.session_state["linkedin_url_cache"] = linkedin_url

                        st.info("Extracting content inventory from resume...")
                        parsed_original = parse_resume_text(resume_text)
                        has_structured  = bool(
                            parsed_original.get("experience")
                            or parsed_original.get("projects")
                        )

                        if has_structured:
                            jd_info["known_companies"] = [
                                exp.get("company", "")
                                for exp in parsed_original.get("experience", [])
                                if exp.get("company")
                            ]
                            jd_info["known_projects"] = [
                                proj.get("title", "")
                                for proj in parsed_original.get("projects", [])
                                if proj.get("title")
                            ]
                            candidate_name = parsed_original.get("name", "")
                        else:
                            inventory = get_known_companies_and_projects(resume_text)
                            jd_info["known_companies"] = inventory["companies"]
                            jd_info["known_projects"]  = inventory["projects"]
                            candidate_name = ""

                        if not candidate_name:
                            parsed_tmp     = parse_resume_text(resume_text)
                            candidate_name = parsed_tmp.get("name", "")

                        st.session_state.candidate_name = candidate_name

                        with st.expander("Detected content (debug)"):
                            st.write("Candidate Name:", candidate_name)
                            st.write("Companies :",     jd_info.get("known_companies", []))
                            st.write("Projects  :",     jd_info.get("known_projects",  []))
                            st.write("JD Skills :",     jd_info.get("skills",          []))
                            st.write("Job Title :",     jd_info.get("job_title",       ""))

                        st.info("Generating tailored resume with AI...")
                        tailored_resume = generate_tailored_resume(resume_text, jd_info)
                        st.session_state.tailored_text = tailored_resume

                        st.info("Validating structure...")
                        validation = validate_resume_content(tailored_resume, jd_info)

                        if not validation["valid"]:
                            st.error("Resume did not pass structural validation.")
                            for err in validation["errors"]:
                                st.warning(f"• {err}")
                            st.stop()

                        st.info("Creating PDF...")
                        timestamp  = int(time.time() * 1000)
                        output_dir = "outputs/pdf"
                        pdf_path   = os.path.join(
                            output_dir, f"tailored_resume_{timestamp}.pdf"
                        )
                        os.makedirs(output_dir, exist_ok=True)

                        generate_resume_latex(tailored_resume, "", pdf_path)

                        with open(pdf_path, "rb") as pdf_file:
                            st.session_state.pdf_bytes = pdf_file.read()

                        st.info("Running AI format verification...")
                        verify_result = verify_resume_format(
                            tailored_resume,
                            candidate_name or "the candidate"
                        )
                        st.session_state.verify_result = verify_result

                        st.success("Resume generated successfully!")

                    except Exception as e:
                        st.error(f"Error: {str(e)}")
                        st.exception(e)

        # ── Download resume ───────────────────────────────────────────────────
        if st.session_state.pdf_bytes:
            st.download_button(
                label="⬇️ Download Resume PDF",
                data=st.session_state.pdf_bytes,
                file_name="tailored_resume.pdf",
                mime="application/pdf",
            )

        # ── Verification report ───────────────────────────────────────────────
        if st.session_state.verify_result:
            vr = st.session_state.verify_result
            st.markdown("---")
            st.subheader("AI Format Verification")
            if vr.get("passed"):
                st.success(f"✅ Format check passed — {vr.get('summary', '')}")
            else:
                st.warning(f"⚠️ Format issues detected — {vr.get('summary', '')}")
                for issue in vr.get("issues", []):
                    st.markdown(f"- {issue}")

            with st.expander("View raw resume text (debug)"):
                st.text(st.session_state.tailored_text or "")

        # ── Cover letter generation ───────────────────────────────────────────
        if generate_cl_btn_top:
            if not st.session_state.get("tailored_text"):
                st.warning("Please generate the resume first.")
            else:
                with st.spinner("Writing cover letter..."):
                    try:
                        cl_data = generate_cover_letter(
                            tailored_resume_text=st.session_state.tailored_text,
                            jd_info=st.session_state.get("jd_info_cache", {}),
                            candidate_name=st.session_state.candidate_name,
                            linkedin_url=st.session_state.get("linkedin_url_cache", ""),
                        )

                        cl_timestamp  = int(time.time() * 1000)
                        cl_output_dir = "outputs/pdf"
                        cl_pdf_path   = os.path.join(
                            cl_output_dir, f"cover_letter_{cl_timestamp}.pdf"
                        )
                        os.makedirs(cl_output_dir, exist_ok=True)

                        generate_cover_letter_latex(cl_data, cl_pdf_path)

                        with open(cl_pdf_path, "rb") as cl_file:
                            st.session_state["cl_bytes"] = cl_file.read()

                        st.success("Cover letter generated!")

                    except Exception as e:
                        st.error(f"Cover letter error: {str(e)}")
                        st.exception(e)

        if st.session_state.get("cl_bytes"):
            st.markdown("---")
            st.subheader("Cover Letter")
            st.download_button(
                label="⬇️ Download Cover Letter PDF",
                data=st.session_state["cl_bytes"],
                file_name="cover_letter.pdf",
                mime="application/pdf",
            )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — EMPLOYER PORTAL  (new RAG shortlisting system)
# ══════════════════════════════════════════════════════════════════════════════

with tab_employer:
    st.title("Employer Portal — Resume Shortlisting")
    st.markdown(
        "Upload candidate resumes into the database, then run a job description "
        "search to instantly rank and shortlist the best matches."
    )

    emp_col1, emp_col2 = st.columns([1, 1.6])

    # ── LEFT: database management + search input ──────────────────────────────
    with emp_col1:

        # ── Resume Database ───────────────────────────────────────────────────
        st.subheader("📁 Resume Database")

        resume_count = get_resume_count()
        st.metric("Resumes in database", resume_count)

        upload_resumes = st.file_uploader(
            "Upload resumes (PDF, multiple allowed)",
            type=["pdf"],
            accept_multiple_files=True,
            key="employer_upload",
        )

        if st.button("➕ Add to Database", use_container_width=True):
            if not upload_resumes:
                st.warning("Please select at least one PDF to upload.")
            else:
                progress = st.progress(0, text="Embedding resumes...")
                added = 0
                for i, f in enumerate(upload_resumes):
                    try:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                            tmp.write(f.getvalue())
                            tmp_path = tmp.name
                        raw_text = parse_resume(tmp_path)
                        os.unlink(tmp_path)

                        add_resume(raw_text, f.name)
                        added += 1
                    except Exception as e:
                        st.warning(f"Failed to process {f.name}: {e}")

                    progress.progress(
                        (i + 1) / len(upload_resumes),
                        text=f"Processed {i + 1}/{len(upload_resumes)}",
                    )
                progress.empty()
                st.success(f"✅ Added {added} resume(s) to database.")
                st.rerun()

        # ── Stored resumes list ───────────────────────────────────────────────
        st.markdown("---")
        st.subheader("Stored Candidates")
        stored = list_resumes()

        if not stored:
            st.info("No resumes in database yet. Upload some above.")
        else:
            for item in stored:
                with st.expander(
                    f"👤 {item.get('name', 'Unknown')}  —  {item.get('filename', '')}",
                    expanded=False,
                ):
                    c1, c2 = st.columns(2)
                    c1.markdown(f"**Email:** {item.get('email', '—')}")
                    c1.markdown(f"**Phone:** {item.get('phone', '—')}")
                    c2.markdown(f"**Uploaded:** {item.get('upload_date', '—')}")
                    st.caption(item.get("preview", "")[:300] + "...")

                    if st.button(
                        "🗑 Delete",
                        key=f"del_{item['id']}",
                        use_container_width=True,
                    ):
                        delete_resume(item["id"])
                        st.success(f"Deleted {item.get('name', item['id'])}")
                        st.rerun()

        # ── Search input ──────────────────────────────────────────────────────
        st.markdown("---")
        st.subheader("🔍 Shortlist Candidates")

        jd_input_method = st.radio(
            "Job Description input method",
            ["Paste text", "Enter URL"],
            horizontal=True,
            key="employer_jd_method",
        )

        jd_text_employer = ""
        if jd_input_method == "Paste text":
            jd_text_employer = st.text_area(
                "Paste the job description here",
                height=200,
                key="employer_jd_text",
            )
        else:
            emp_jd_url = st.text_input(
                "Job URL",
                placeholder="https://example.com/job-posting",
                key="employer_jd_url",
            )
            if emp_jd_url and st.button("Fetch JD", key="employer_fetch_jd"):
                with st.spinner("Fetching job description..."):
                    try:
                        jd_text_employer = scrape_job_description(emp_jd_url)
                        st.session_state["employer_fetched_jd"] = jd_text_employer
                        st.success("Job description fetched.")
                    except Exception as e:
                        st.error(f"Failed to fetch JD: {e}")
            jd_text_employer = st.session_state.get("employer_fetched_jd", "")

        top_k = st.slider(
            "Number of candidates to retrieve",
            min_value=1, max_value=20, value=5, step=1,
            key="employer_top_k",
        )

        use_llm_scoring = st.toggle(
            "Enable AI scoring (slower, more detailed)",
            value=True,
            key="employer_llm_scoring",
        )

        run_btn = st.button(
            "🚀 Run Shortlisting",
            use_container_width=True,
            key="employer_run",
            disabled=(get_resume_count() == 0),
        )

    # ── RIGHT: results ────────────────────────────────────────────────────────
    with emp_col2:
        st.subheader("📊 Shortlisting Results")

        if run_btn:
            if not jd_text_employer.strip():
                st.error("Please provide a job description.")
            else:
                with st.spinner(
                    "Searching database and scoring candidates... "
                    "This may take a minute."
                ):
                    try:
                        results = shortlist(
                            jd_text   = jd_text_employer,
                            top_k     = top_k,
                            llm_score = use_llm_scoring,
                        )
                        st.session_state.shortlist_results = results
                        st.session_state.shortlist_run     = True
                    except Exception as e:
                        st.error(f"Shortlisting failed: {str(e)}")
                        st.exception(e)

        if st.session_state.shortlist_run:
            results = st.session_state.shortlist_results

            if not results:
                st.warning("No matching candidates found.")
            else:
                st.success(f"Found {len(results)} candidate(s) — ranked by match score.")

                # ── Summary table ─────────────────────────────────────────────
                import pandas as pd

                table_data = []
                for rank, r in enumerate(results, 1):
                    table_data.append({
                        "Rank":       rank,
                        "Name":       r.get("name",     "—"),
                        "Email":      r.get("email",    "—"),
                        "Score":      f"{r.get('llm_score', r.get('combined_score', 0))}%",
                        "Skill Match":f"{r.get('skill_match', '—')}%" if use_llm_scoring else "—",
                        "Exp Match":  f"{r.get('experience_match', '—')}%" if use_llm_scoring else "—",
                        "File":       r.get("filename", "—"),
                    })

                st.dataframe(
                    pd.DataFrame(table_data),
                    use_container_width=True,
                    hide_index=True,
                )

                # ── Detailed candidate cards ───────────────────────────────────
                st.markdown("---")
                st.subheader("Candidate Details")

                for rank, r in enumerate(results, 1):
                    score     = r.get("llm_score", r.get("combined_score", 0))
                    bar_color = (
                        "🟢" if score >= 70
                        else "🟡" if score >= 45
                        else "🔴"
                    )

                    with st.expander(
                        f"{bar_color} #{rank}  {r.get('name', 'Unknown')}  —  "
                        f"Score: {score}%",
                        expanded=(rank == 1),
                    ):
                        info_col, score_col = st.columns([1.5, 1])

                        with info_col:
                            st.markdown(f"**Email:** {r.get('email', '—')}")
                            st.markdown(f"**Phone:** {r.get('phone', '—')}")
                            st.markdown(f"**File:**  {r.get('filename', '—')}")
                            st.markdown(f"**Uploaded:** {r.get('upload_date', '—')}")

                        with score_col:
                            if use_llm_scoring:
                                st.metric("Overall",    f"{r.get('llm_score', 0)}%")
                                st.metric("Skill Match",f"{r.get('skill_match', 0)}%")
                                st.metric("Experience", f"{r.get('experience_match', 0)}%")
                                st.metric("Education",  f"{r.get('education_match', 0)}%")
                            else:
                                st.metric("Semantic Score", f"{r.get('combined_score', 0)}%")
                                sec = r.get("section_scores", {})
                                if sec:
                                    st.caption(
                                        f"Skills: {sec.get('skills', 0)}%  |  "
                                        f"Exp: {sec.get('experience', 0)}%  |  "
                                        f"Summary: {sec.get('summary', 0)}%"
                                    )

                        if use_llm_scoring and r.get("justification"):
                            st.markdown("**AI Assessment:**")
                            st.info(r["justification"])

                        s_col, g_col = st.columns(2)
                        with s_col:
                            strengths = r.get("strengths", [])
                            if strengths:
                                st.markdown("**✅ Strengths:**")
                                for s in strengths:
                                    st.markdown(f"- {s}")
                        with g_col:
                            gaps = r.get("skill_gaps", [])
                            if gaps:
                                st.markdown("**⚠️ Skill Gaps:**")
                                for g in gaps:
                                    st.markdown(f"- {g}")

                        # Resume preview
                        with st.expander("Resume Preview", expanded=False):
                            st.caption(r.get("preview", "No preview available."))