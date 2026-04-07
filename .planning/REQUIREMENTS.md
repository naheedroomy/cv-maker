# Requirements — CV Maker v3.0 Deploy, Auth & CV Editor

## Milestone v3.0 Requirements

### Deployment

- [x] **DEPLOY-01**: App runs as Docker containers (backend + frontend) orchestrated by docker-compose
- [x] **DEPLOY-02**: Backend Docker image includes Python runtime, LaTeX (texlive), and all Python dependencies
- [x] **DEPLOY-03**: Frontend Docker image builds Vue SPA and serves it via Nginx
- [x] **DEPLOY-04**: GitHub Actions workflow builds images and deploys to VPS via SSH on push to main
- [x] **DEPLOY-05**: Nginx routes `/api/*` requests to backend container and `/` to frontend SPA
- [ ] **DEPLOY-06**: App is accessible via a domain name (HTTPS handled by Nginx + certbot or reverse proxy)

### Authentication

- [x] **AUTH-01**: User can sign in using their Google account (Google OAuth 2.0 via ID token)
- [x] **AUTH-02**: Backend verifies Google ID token and issues a signed JWT stored in localStorage
- [x] **AUTH-03**: All `/api/*` endpoints require a valid JWT (middleware returns 401 if missing/invalid)
- [x] **AUTH-04**: Frontend Vue Router guards redirect unauthenticated users to the sign-in page
- [x] **AUTH-05**: User can sign out, which clears the JWT from localStorage
- [x] **AUTH-06**: User's name and profile picture from Google are displayed in the app header/sidebar

### Multi-Tenant Data

- [x] **TENANT-01**: Users table is created automatically on first sign-in (google_id, email, name, created_at)
- [x] **TENANT-02**: All CV tailoring jobs are scoped to the authenticated user (user_id FK on jobs table)
- [x] **TENANT-03**: Settings (model preferences, base URL) are stored and loaded per user
- [x] **TENANT-04**: API keys (Anthropic, Gemini, OpenAI) are stored and resolved per user
- [x] **TENANT-05**: Users can only view and interact with their own data — no cross-user data leakage

### CV Editor

- [x] **CVED-01**: User can upload a PDF or DOCX file containing their existing CV
- [x] **CVED-02**: AI parses the uploaded CV and extracts structured data matching the BaseCV model (experience, skills, education, summary, contact)
- [x] **CVED-03**: User sees a visual sectioned editor with their parsed CV (Work Experience, Education, Skills, Summary, Contact)
- [x] **CVED-04**: User can add, edit, and delete individual entries within each CV section
- [x] **CVED-05**: User can save their CV and it persists in the DB under their account
- [x] **CVED-06**: The saved CV is used as the base CV when tailoring new job applications

---

## Future Requirements

- Email/password login as fallback to Google (future milestone)
- Admin dashboard for user management (future milestone)
- CV version history / undo (future milestone)
- Multiple saved CV variants per user (future milestone)
- Visual template selector for PDF output (backlog — 999.1)
- LaTeX CV preview in editor (future milestone)
- HTTPS / TLS cert automation via certbot (manual setup initially)

---

## Out of Scope (v3.0)

- Email/password account creation — Google-only auth for v3.0
- Job listing URL scraping — copy-paste is sufficient
- Multiple CV format templates — one good template first
- Job application tracking — CV generator, not ATS
- Axios HTTP client — supply chain compromise (use native fetch)
- Payment / billing — free service
- Admin dashboard / user management UI

---

## Traceability

| REQ-ID | Phase | Plan | Status |
|--------|-------|------|--------|
| TENANT-01 | 1002 | 1002-01, 1002-03 | ○ |
| TENANT-02 | 1002 | 1002-01, 1002-03 | ○ |
| TENANT-03 | 1002 | 1002-02, 1002-03 | ○ |
| TENANT-04 | 1002 | 1002-02, 1002-03 | ○ |
| TENANT-05 | 1002 | 1002-01, 1002-02, 1002-03 | ○ |
| AUTH-01 | 1003 | TBD | ○ |
| AUTH-02 | 1003 | TBD | ○ |
| AUTH-03 | 1003 | TBD | ○ |
| AUTH-04 | 1003 | TBD | ○ |
| AUTH-05 | 1003 | TBD | ○ |
| AUTH-06 | 1003 | TBD | ○ |
| CVED-01 | 1004 | TBD | ○ |
| CVED-02 | 1004 | TBD | ○ |
| CVED-03 | 1004 | TBD | ○ |
| CVED-04 | 1004 | TBD | ○ |
| CVED-05 | 1004 | TBD | ○ |
| CVED-06 | 1004 | TBD | ○ |
| DEPLOY-01 | 1005 | TBD | ○ |
| DEPLOY-02 | 1005 | TBD | ○ |
| DEPLOY-03 | 1005 | TBD | ○ |
| DEPLOY-05 | 1005 | TBD | ○ |
| DEPLOY-04 | 1006 | TBD | ○ |
| DEPLOY-06 | 1006 | TBD | ○ |
