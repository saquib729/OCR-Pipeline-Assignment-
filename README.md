# 🧾 OCR Based Medical Document Text Extraction & PII Redaction

This project extracts text from scanned medical documents (including handwritten notes) and automatically detects and redacts **Personally Identifiable Information (PII)** such as Patient Name, IPD Number, UHID, Age, Sex, Phone Number, Dates, etc.  

It uses **EasyOCR** for handwritten and printed OCR and **OpenCV** for redaction operations.  
This project ensures secure and privacy–preserving conversion of physical health records into digital format.

---

## 🚀 Features

- Extracts text from medical forms and case sheets
- Supports both printed and handwritten text
- Detects PII like Patient Name, IPD No., UHID, Age, Sex, Dates, Phone Numbers
- Automatically redacts PII by masking text on the image
- Saves:
  - Extracted text (`*_text.txt`)
  - Detected PII details (`*_pii.txt`)
  - Redacted medical images (`*_redacted.jpg`)
- Works **offline** — no cloud dependency
- Lightweight and easy to run

---

## 🛠️ Technologies Used

| Technology | Purpose |
|-----------|---------|
| Python | Main programming language |
| EasyOCR | OCR for handwriting & printed text |
| OpenCV | Image processing + black box redaction |
| Regex | Pattern matching for PII |
| Pillow | Image handling |

---

## 📂 Project Structure
project/
├── easy_ocr_pii.py # Main Script
├── images/ # Input medical images
└── outputs/ # Output: Text + redacted images

---

## ⚙️ How to Run the Project

### ✔️ Step 1: Install Dependencies using requirements.txt
✔️ Step 2: Add Input Files
Place your .jpg / .jpeg / .png documents in the images folder.

✔️ Step 3: Run the Script
python easy_ocr_pii.py

✔️ Step 4: Check Output

Redacted results will be in the outputs folder:

Output File	Description
*_text.txt	Extracted text file
*_pii.txt	Detected PII report
*_redacted.jpg	Redacted image with blacked-out PII

## 📂 Project Structure

