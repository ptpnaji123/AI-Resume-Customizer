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
from generator.generate_latex import generate_resume_latex, parse_resume_text
from ai_engine.cover_letter import generate_cover_letter
from generator.cover_letter_latex import generate_cover_letter_latex

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="Resume Tailor AI", page_icon="📄")

if "pdf_bytes"      not in st.session_state:
    st.session_state.pdf_bytes      = None
if "verify_result"  not in st.session_state:
    st.session_state.verify_result  = None
if "tailored_text"  not in st.session_state:
    st.session_state.tailored_text  = None
if "candidate_name" not in st.session_state:
    st.session_state.candidate_name = ""

st.title("Resume Tailor AI")
st.markdown("Tailor your resume for any job application using AI")

# ── Layout ────────────────────────────────────────────────────────────────────
col1, col2 = st.columns([1, 1])

with col1:
    st.header("Job Description")
    jd_url = st.text_input(
        "Enter Job URL",
        placeholder="https://example.com/job-posting"
    )

    st.header("Upload Base Resume")
    uploaded_file = st.file_uploader("Upload your resume (PDF)", type=["pdf"])

    linkedin_url = st.text_input(
        "LinkedIn Profile URL",
        placeholder="https://www.linkedin.com/in/your-profile"
    )

    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        generate_btn = st.button("📄 Generate Resume", use_container_width=True)
    with btn_col2:
        generate_cl_btn_top = st.button(
            "✉️ Generate Cover Letter",
            use_container_width=True,
            disabled=not bool(st.session_state.get('tailored_text')),
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
                    # ── Step 1: Scrape JD ─────────────────────────────────────
                    st.info("Scraping job description...")
                    jd_text = scrape_job_description(jd_url)

                    # ── Step 2: Extract JD requirements ───────────────────────
                    st.info("Extracting skills and keywords from JD...")
                    jd_info = extract_skills_and_keywords(jd_text)
                    st.session_state['jd_info_cache'] = jd_info

                    # ── Step 3: Parse resume PDF ──────────────────────────────
                    st.info("Parsing your resume...")
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                        tmp.write(uploaded_file.getvalue())
                        tmp_path = tmp.name
                    resume_text = parse_resume(tmp_path)
                    os.unlink(tmp_path)

                    # ── Inject LinkedIn URL into resume text if provided ──────
                    # The inventory extractor reads raw text, so prepending the
                    # URL here means it will be found and added to the header.
                    if linkedin_url and linkedin_url.strip():
                        resume_text = f"LinkedIn: {linkedin_url.strip()}\n" + resume_text
                    st.session_state['linkedin_url_cache'] = linkedin_url

                    # ── Step 4: Extract known companies & projects ────────────
                    st.info("Extracting content inventory from resume...")
                    parsed_original = parse_resume_text(resume_text)
                    has_structured  = bool(
                        parsed_original.get('experience')
                        or parsed_original.get('projects')
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

                    # Try to get name from raw text if not found
                    if not candidate_name:
                        parsed_tmp = parse_resume_text(resume_text)
                        candidate_name = parsed_tmp.get("name", "")

                    st.session_state.candidate_name = candidate_name

                    # Debug expander
                    with st.expander("Detected content (debug)"):
                        st.write("Candidate Name:", candidate_name)
                        st.write("Companies :", jd_info.get("known_companies", []))
                        st.write("Projects  :", jd_info.get("known_projects",  []))
                        st.write("JD Skills :", jd_info.get("skills",          []))
                        st.write("Job Title :", jd_info.get("job_title",       ""))

                    # ── Step 5: Generate tailored resume ──────────────────────
                    st.info("Generating tailored resume with AI...")
                    tailored_resume = generate_tailored_resume(resume_text, jd_info)
                    st.session_state.tailored_text = tailored_resume

                    # ── Step 6: Validate structure ────────────────────────────
                    st.info("Validating structure...")
                    validation = validate_resume_content(tailored_resume, jd_info)

                    if not validation["valid"]:
                        st.error("Resume did not pass structural validation.")
                        for err in validation["errors"]:
                            st.warning(f"• {err}")
                        st.stop()

                    # ── Step 7: Compile LaTeX → PDF ───────────────────────────
                    st.info("Creating PDF...")
                    timestamp  = int(time.time() * 1000)
                    output_dir = "outputs/pdf"
                    pdf_path   = os.path.join(output_dir, f"tailored_resume_{timestamp}.pdf")
                    os.makedirs(output_dir, exist_ok=True)

                    generate_resume_latex(tailored_resume, "", pdf_path)

                    with open(pdf_path, "rb") as pdf_file:
                        st.session_state.pdf_bytes = pdf_file.read()

                    # ── Step 8: AI format verification ────────────────────────
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

    # ── Download button ───────────────────────────────────────────────────────
    if st.session_state.pdf_bytes:
        st.download_button(
            label="⬇️ Download PDF",
            data=st.session_state.pdf_bytes,
            file_name="tailored_resume.pdf",
            mime="application/pdf",
        )

    # ── AI Verification Report ────────────────────────────────────────────────
    if st.session_state.verify_result:
        vr = st.session_state.verify_result
        st.markdown("---")
        st.subheader("AI Format Verification")

        if vr.get("passed"):
            st.success(f"✅ Format check passed — {vr.get('summary', '')}")
        else:
            st.warning(f"⚠️ Format issues detected — {vr.get('summary', '')}")
            issues = vr.get("issues", [])
            if issues:
                for issue in issues:
                    st.markdown(f"- {issue}")
            else:
                st.markdown("No specific issues listed.")

        # Optionally show raw LLM output text for debugging
        with st.expander("View raw resume text (debug)"):
            st.text(st.session_state.tailored_text or "")


    # ── Cover Letter generation (triggered by top button) ────────────────────
    if generate_cl_btn_top:
        if not st.session_state.get("tailored_text"):
            st.warning("Please generate the resume first.")
        else:
            with st.spinner("Writing cover letter..."):
                try:
                    cl_data = generate_cover_letter(
                        tailored_resume_text = st.session_state.tailored_text,
                        jd_info              = st.session_state.get("jd_info_cache", {}),
                        candidate_name       = st.session_state.candidate_name,
                        linkedin_url         = st.session_state.get("linkedin_url_cache", ""),
                    )

                    cl_timestamp  = int(time.time() * 1000)
                    cl_output_dir = "outputs/pdf"
                    cl_pdf_path   = os.path.join(cl_output_dir, f"cover_letter_{cl_timestamp}.pdf")
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