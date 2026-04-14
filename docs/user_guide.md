# User Guide: CPS (Quick Track System)

Welcome to the Quick Track Check Processing System. This application enables your accounting and processing center to vastly reduce manual data entry when dealing with incoming checks by utilizing AI-powered Optical Character Recognition.

This guide provides step-by-step instructions for the standard processing lifecycle.

---

## 1. Logging In

Before you can process any checks, you must log in:
1. Navigate to the web application URL.
2. Enter your assigned **Username** and **Password**.
3. If you have administrative privileges, you will see additional dashboard items (like the Audit Log).

---

## 2. Uploading Checks

A typical stack of checks should be scanned into a multi-page PDF or individual image files (`.jpg`, `.png`).

1. Open the **Upload** panel (usually visible on the dashboard or by clicking "Upload Checks" in the navigation).
2. **Drag & Drop** your PDF or Image files into the dashed upload area. Alternatively, click the area to natively select files from your computer.
3. Click the **Process** button.
4. The system will create a **Batch**. Do not close the window if a loading bar is visible. The system works rapidly (usually ~3 seconds per page).

---

## 3. The Dashboard & Monitoring

Once your files finish uploading, you'll be redirected to the main **Dashboard**.

- You will see a table listing recent **Batches**.
- A single Batch represents one upload session and may contain dozens of individual checks.
- Look at the **Status Column**:
  - `processing`: The AI is currently reviewing the checks.
  - `needs_review`: One or more checks failed rigorous validation and require a human to perform a visual check.
  - `approved`: All checks in the batch successfully passed validation algorithms.

---

## 4. Manual Review & Correction

The AI is highly accurate, but things like bad handwriting or poor scan quality can occasionally confuse it—especially on Routing or Account numbers.

1. Click on a Batch that says `needs_review`.
2. A list of all checks in that batch will expand. Problematic checks will be highlighted or explicitly marked as `Review Required`.
3. Click **Review** on the flagged check.
4. A split-screen window will appear:
   - **Left Side:** A clear view of the uploaded Check scan.
   - **Right Side:** The extracted data fields (Payee, Routing Number, Account Number, Amount).
5. Compare the Right Side with the actual images on the Left. 
6. Correct any obvious mistakes (e.g., if a Routing Number is 8 digits long instead of 9, look at the check bottom line and append the missing digit).
7. Once corrected, change the status drop-down from `needs_review` to `approved` and save.

> **Note:** Any changes you make are explicitly logged in the **Audit History** to track modifications for compliance.

---

## 5. Exporting to Excel/CSV

To bring this data into your accounting software (e.g., QuickBooks, Xero, standard proprietary databases):

1. Once a batch is fully `approved`, return to the Dashboard.
2. Ensure you have selected the batches you want to export.
3. Click the **Export to Excel** or **Export to CSV** button on the top right.
4. A standardized spreadsheet will be downloaded directly to your PC, containing cleanly separated columns for Memo, Amount, Account Numbers, etc.
