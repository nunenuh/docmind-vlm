# User Stories Definition: DocMind-VLM

**Project:** DocMind-VLM
**Owner:** Erfan
**Date:** 2026-03-11
**Status:** Product Definition

---

## Landing Page

- **US-0a:** As a visitor, I want to see what DocMind-VLM does within 5 seconds of landing so that I can decide whether to sign up.
- **US-0b:** As a visitor, I want to see a live demo preview or video of the product in action so that I understand the value before committing to an account.
- **US-0c:** As a visitor, I want to see the feature highlights (extraction, confidence overlay, comparison, chat) so that I understand what makes this different from other document AI tools.
- **US-0d:** As a hiring manager, I want to see the tech stack and architecture credibility on the landing page so that I can assess the technical depth before cloning the repo.
- **US-0e:** As a visitor, I want a clear call-to-action to sign in so that I can start using the product immediately after being convinced.

## Authentication

- **US-1:** As a user, I want to log in with my Google or GitHub account so that I can access the application without creating a new password.
- **US-2:** As a user, I want my documents to be private so that only I can see and access my uploaded files.
- **US-3:** As a user, I want to stay logged in across browser sessions so that I don't have to re-authenticate every time.

## Document Upload

- **US-4:** As a user, I want to drag and drop a document (PDF or image) into the upload area so that I can start processing quickly.
- **US-5:** As a user, I want to see upload progress so that I know my file is being transferred.
- **US-6:** As a user, I want clear error messages if my file is too large or in an unsupported format so that I know what to fix.

## Document Processing

- **US-7:** As a user, I want to see real-time progress of the processing pipeline (deskew, quality check, VLM extraction) so that I understand what's happening and don't think the app is frozen.
- **US-8:** As a user, I want the system to automatically detect and correct skewed/tilted document images so that I get better extraction results from imperfect scans.

## Extraction — General Mode

- **US-9:** As a user, I want to upload any document type and get extracted key-value pairs, tables, and entities without selecting a template so that I can quickly process unfamiliar documents.
- **US-10:** As a user, I want to see the extracted data as structured JSON so that I can copy it or feed it into other tools.

## Extraction — Template Mode

- **US-11:** As a user, I want to select a document type (invoice, receipt, contract, certificate) so that the system extracts specific fields I care about with validation.
- **US-12:** As a user, I want the system to auto-detect the document type so that I don't have to manually choose a template every time.
- **US-13:** As a user, I want to see which required fields are missing from the extraction so that I know the document may be incomplete or the scan quality was too low.

## Audit Trail & Transparency

- **US-14:** As a user, I want to click on any extracted field and see where in the document it came from (highlighted source region) so that I can verify the extraction is correct.
- **US-15:** As a user, I want to see a confidence score for each extracted field so that I know which fields to trust and which to double-check.
- **US-16:** As a user, I want to see what preprocessing steps were applied (deskew, denoise, etc.) so that I understand how the system processed my document.

## Confidence Overlay

- **US-17:** As a user, I want to see a visual heatmap on my document showing high/medium/low confidence regions so that I can quickly spot problematic areas.
- **US-18:** As a user, I want to see explanatory notes on low-confidence regions (e.g., "blur detected", "region truncated") so that I understand WHY confidence is low.

## Pipeline Comparison

- **US-19:** As a user, I want to see a side-by-side comparison of "raw VLM output" vs "DocMind-VLM enhanced output" so that I can understand the value of the enhanced pipeline.
- **US-20:** As a user, I want visual highlighting of fields that were corrected or added by the enhanced pipeline so that the difference is obvious at a glance.

## Document Chat

- **US-21:** As a user, I want to ask natural language questions about my uploaded document so that I can find information without manually scanning pages.
- **US-22:** As a user, I want every chat answer to include a citation (page, region, text span) so that I can verify the answer against the original document.
- **US-23:** As a user, I want to have multi-turn conversations so that I can ask follow-up questions based on previous answers.
- **US-24:** As a user, I want my chat history saved per document so that I can return to a previous conversation later.

## Export

- **US-25:** As a user, I want to export extracted data as JSON or CSV so that I can use it in spreadsheets or other systems.
- **US-26:** As a user, I want to copy the chat summary to my clipboard so that I can paste it into a report or email.

## Portfolio / Demo

- **US-27:** As a hiring manager, I want to run `docker compose up` and have the full application working within 5 minutes so that I can evaluate the candidate's project quickly.
- **US-28:** As a hiring manager, I want to see pre-loaded example documents so that I can try the demo immediately without having my own test files.

---
#user-stories #requirements #user-centric #docmind-vlm
