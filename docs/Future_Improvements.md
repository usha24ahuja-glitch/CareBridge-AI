# Future Improvements: CareBridge AI

This roadmap outlines prospective features and system enhancements for transitioning CareBridge AI from a workflow prototype into an enterprise-ready healthcare platform.

---

## 📈 Roadmap & Enhancements

### 1. EHR & FHIR Integration
- **Direct EHR Syncing**: Integrate with standard Electronic Health Record (EHR) systems (e.g., Epic, Cerner, Athenahealth) using FHIR (Fast Healthcare Interoperability Resources) APIs.
- **Auto-populate Charts**: Automatically write the completed HRSN screening summary directly into the patient's chart as a structured document or clinical note (e.g., SOAP note format).
- **Patient Context Loading**: Retrieve patient age, language, and contact details from the EHR to automatically pre-populate the screening intake.

### 2. Expanded Patient Communication Channels
- **Patient Self-Screening**: Create patient-facing chat interfaces via SMS (Twilio) or WhatsApp to allow patients to complete the screening before their appointment, importing results directly into the clinic's Slack interface for review.
- **Multi-lingual AI Translation**: Support real-time conversational screening translation in Spanish, Vietnamese, Arabic, and other common non-English languages spoken by clinic populations.

### 3. Integrated Referral Directories
- **Findhelp / Unite Us API Sync**: Connect to national and regional social service registries (like Findhelp/Aunt Bertha or Unite Us) to query thousands of up-to-date community resources, rather than relying on a static local registry file.
- **Referral Loop Closure**: Allow community partners to update the referral status inside their own system, triggering an event that posts resolution updates back to the clinic's Slack channel (e.g. marking a housing referral as "Resolved - Housed").

### 4. Advanced Analytics & Machine Learning
- **Geospatial Need Mapping**: Use geographic information systems (GIS) to overlay screening positive rates on maps to identify hot spots of food insecurity or transportation deserts in specific neighborhoods.
- **Predicative SDoH Modeling**: Use aggregate historical data to identify which clinical symptoms correlate with high-risk social needs to proactively suggest screenings during appointment booking.

### 5. Security & Compliance (Enterprise Readiness)
- **HIPAA Compliance & BAAs**: Transition data storage from plain JSON files to HIPAA-compliant relational databases with database-level encryption at rest. Establish Business Associate Agreements (BAAs) with API hosts.
- **Auditing Logs**: Maintain immutable audit logs tracking who accessed patient screening summaries, ensuring compliance with health information privacy standards.
