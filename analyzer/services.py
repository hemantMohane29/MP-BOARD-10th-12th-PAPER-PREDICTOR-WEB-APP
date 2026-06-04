import os
import json
import time
import socket
from django.conf import settings
from google import genai
from google.genai import types
from dotenv import load_dotenv
import zipfile
import tempfile
from sarvamai import SarvamAI
from .models import ExamPaper

load_dotenv(override=True)

def get_fresh_sarvam_key():
    """Reloads .env and returns the current Sarvam API key."""
    load_dotenv(override=True)
    key = os.environ.get("SARVAM_API_KEY", "")
    if key:
        print(f"[Debug] Using Sarvam Key starting with: {key[:8]}...")
    return key

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

client = genai.Client(api_key=GEMINI_API_KEY)

CLASS_12_SYLLABUS = {
    "Biology": [
        "अध्याय-1 पुष्पी पादपों में लैंगिक प्रजनन", "अध्याय-2 मानव जनन", "अध्याय-3 जनन स्वास्थ्य",
        "अध्याय-4 वंशागति तथा विविधता के सिद्धांत", "अध्याय-5 वंशागति के आणविक आधार", "अध्याय-6 विकास",
        "अध्याय-7 मानव स्वास्थ्य तथा रोग", "अध्याय-8 मानव कल्याण में सूक्ष्मजीव", "अध्याय-9 जैव प्रौद्योगिकी- सिद्धांत व प्रक्रम",
        "अध्याय-10 जैव प्रौद्योगिकी एवं उसके उपयोग", "अध्याय-11 जीव और समष्टियाँ", "अध्याय-12 पारितंत्र", "अध्याय-13 जैव-विविधता एवं संरक्षण"
    ],
    "Physics": [
        "अध्याय 1- वैद्युत आवेश तथा क्षेत्र", "अध्याय 2- स्थिरवैद्युत विभव तथा धारिता", "अध्याय 3- विद्युत धारा",
        "अध्याय 4- गतिमान आवेश और चुंबकत्व", "अध्याय 5- चुंबकत्व एवं द्रव्य", "अध्याय 6- वैद्युतचुंबकीय प्रेरण",
        "अध्याय 7- प्रत्यावर्ती धारा", "अध्याय 8- वैद्युतचुंबकीय तरंगें", "अध्याय 9- किरण प्रकाशिकी एवं प्रकाशिक यंत्र",
        "अध्याय 10- तरंग प्रकाशिकी", "अध्याय 11- विकिरण तथा द्रव्य की द्वैत प्रकृति", "अध्याय 12- परमाणु",
        "अध्याय 13- नाभिक", "अध्याय 14- अर्धचालक इलेक्ट्रॉनिकी- पदार्थ, युक्तियाँ तथा सरल परिपथ"
    ],
    "Maths": [
        "अध्याय-1 संबंध एवं फलन", "अध्याय-2 प्रतिलोम त्रिकोणमितीय फलन", "अध्याय-3 आव्यूह", "अध्याय-4 सारणिक",
        "अध्याय-5 सांतत्य तथा अवकलनीयता", "अध्याय-6 अवकलज के अनुप्रयोग", "अध्याय-7 समाकलन", "अध्याय-8 समाकलनों के अनुप्रयोग",
        "अध्याय-9 अवकल समीकरण", "अध्याय-10 सदिश बीजगणित", "अध्याय-11 त्रि-विमीय ज्यामिति", "अध्याय-12 रैखिक प्रोग्रामन", "अध्याय-13 प्रायिकता"
    ],
    "Chemistry": [
        "Unit-1 विलयन", "Unit-2 वैद्युतरसायन", "Unit-3 रासायनिक बलगतिकी", "Unit-4 d- एवं f- ब्लॉक के तत्व",
        "Unit-5 उपसहसंयोजन यौगिक", "Unit-6 हैलोऐल्केन तथा हैलोऐरीन", "Unit-7 ऐल्कोहॉल, फ़ीनॉल एवं ईथर",
        "Unit-8 ऐल्डिहाइड, कीटोन एवं कार्बोक्सिलिक अम्ल", "Unit-9 ऐमीन", "Unit-10 जैव-अणु"
    ]
}

CLASS_10_SYLLABUS = {
    "Maths": [
        "अध्याय-1 वास्तविक संख्याएँ", "अध्याय-2 बहुपद", "अध्याय-3 दो चर वाले रैखिक समीकरण युग्म",
        "अध्याय-4 द्विघात समीकरण", "अध्याय-5 समांतर श्रेढ़ियाँ", "अध्याय-6 त्रिभुज",
        "अध्याय-7 निर्देशांक ज्यामिति", "अध्याय-8 त्रिकोणमिति का परिचय", "अध्याय-9 त्रिकोणमिति के कुछ अनुप्रयोग",
        "अध्याय-10 वृत्त", "अध्याय-11 वृत्तों से संबंधित क्षेत्रफल", "अध्याय-12 पृष्ठीय क्षेत्रफल और आयतन",
        "अध्याय-13 सांख्यिकी", "अध्याय-14 प्रायिकता"
    ],
    "Hindi": [
        "क्षितिज भाग - 2 काव्य खण्ड", "काव्य बोध", "क्षितिज भाग - 2 गद्य खण्ड",
        "भाषा बोध", "कृतिका भाग-2", "अपठित बोध", "पत्र लेखन", "अनुच्छेद लेखन/निबंध लेखन"
    ],
    "Sindhi": [
        "गद्य अंश (Prose)", "पद्य अंश (Poetry)", "व्याकरण (Grammer)",
        "शब्दावली / सहायक वाचन (Vocabulary/ R. read)", "निबन्ध (Essay)",
        "पत्र लेखन / आवेदन पत्र (Letter / Application)", "अपठित गद्यांश (Unseen Part)"
    ],
    "Science": [
        "रासायनिक अभिक्रियाएं एवं समीकरण", "अम्ल क्षार एवं लवण", "धातु एवं अधातु",
        "कार्बन एवं उसके यौगिक", "जैव प्रक्रम", "नियंत्रण एवं समन्वय",
        "जीव जनन कैसे करते हैं?", "अनुवांशिकता", "प्रकाश परावर्तन एवं अपवर्तन",
        "मानव नेत्र एवं रंग बिरंगा संसार", "विद्युत", "विद्युत धारा के चुंबकीय प्रभाव",
        "हमारा पर्यावरण"
    ]
}

SAFETY_SETTINGS = [
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
        threshold=types.HarmBlockThreshold.BLOCK_NONE,
    ),
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
        threshold=types.HarmBlockThreshold.BLOCK_NONE,
    ),
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        threshold=types.HarmBlockThreshold.BLOCK_NONE,
    ),
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        threshold=types.HarmBlockThreshold.BLOCK_NONE,
    ),
]

GENERATE_CONFIG = types.GenerateContentConfig(
    safety_settings=SAFETY_SETTINGS,
    temperature=0.3,
)

class AIPipelineOrchestrator:
    def __init__(self):
        # Default to best available model — actual fallback happens at call time
        self.model_name = 'gemini-2.5-flash'
        print(f"[Analyzer] Using model: {self.model_name}")
        
    FALLBACK_MODELS = [
        'gemini-3-flash-preview',
        'gemini-3.1-flash-lite-preview',
        'gemini-3-pro-preview',
        'gemini-2.5-flash',
        'gemini-flash-lite-latest',
    ]

    def _call_with_model_fallback(self, build_request_fn):
        last_error = None
        for model_name in self.FALLBACK_MODELS:
            try:
                print(f"[Pipeline] Trying model: {model_name}")
                result = build_request_fn(model_name)
                print(f"[Pipeline] Success with model: {model_name}")
                return result
            except Exception as e:
                print(f"[Pipeline] Model {model_name} failed: {str(e)[:120]}")
                with open(os.path.join(settings.BASE_DIR, "error_log.txt"), "a") as f:
                    f.write(f"\n[Model Fallback Error] {model_name}: {e}\n")
                last_error = e
                time.sleep(2)
        raise last_error

    def _safe_get_text(self, response):
        try:
            return response.text
        except ValueError:
            if response.candidates:
                candidate = response.candidates[0]
                if candidate.content and candidate.content.parts:
                    return candidate.content.parts[0].text
            print(f"Warning: Response blocked. Finish reason: {response.candidates[0].finish_reason if response.candidates else 'unknown'}")
            return ""

    def validate_paper_content(self, text=None, image_path=None, subject=None):
        """
        Uses Gemini to verify if the content is a school/college academic question paper.
        Throws ValueError if irrelevant or not in the expected language.
        """
        if subject == 'English':
            expected_lang = "English (अंग्रेजी)"
            lang_instruction = "Is the primary language of the questions English? Since this is an English language paper, the questions and text must be in English."
        elif subject == 'Hindi':
            expected_lang = "Hindi (हिंदी)"
            lang_instruction = "Is the primary language of the questions Hindi? Since this is a Hindi paper, it should be entirely in Hindi."
        else:
            expected_lang = "Hindi (हिंदी) medium (allowing bilingual English translations, scientific terms, or mathematical expressions)"
            lang_instruction = "Is the primary language of the questions Hindi? Note that it is perfectly fine if there are some English words, scientific terms, mathematical expressions, or English translations alongside the Hindi text, as long as the paper is fundamentally a Hindi medium paper."

        prompt = f"""
        Analyze the following content. You must determine:
        1. Is this a school/college academic question paper (specifically for boards like MP Board)?
        2. {lang_instruction}
        
        Answer ONLY in JSON format:
        {{
            "is_question_paper": true,
            "is_hindi": true,
            "confidence_score": 0.95,
            "reason_if_invalid": "Short explanation in Hindi why it was rejected"
        }}
        
        Note: For the "is_hindi" field, set it to true if the paper matches the expected language/medium: {expected_lang}.
        """
        
        def _call_validation(model_name):
            contents = [prompt]
            if image_path:
                with open(image_path, 'rb') as f:
                    image_data = f.read()
                mime = 'image/jpeg'
                if image_path.lower().endswith('.png'): mime = 'image/png'
                contents.append(types.Part.from_bytes(data=image_data, mime_type=mime))
            else:
                contents.append(f"Sample Text: {text[:8000]}")
                
            response = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=GENERATE_CONFIG
            )
            res_text = self._safe_get_text(response)
            return self._parse_gemini_json_response(res_text)

        result = self._call_with_model_fallback(_call_validation)
        
        if not result.get('is_question_paper') or not result.get('is_hindi', True):
            reason = result.get('reason_if_invalid', "यह फ़ाइल एक वैध प्रश्न पत्र नहीं लग रही है।")
            raise ValueError(f"Validation Failed: {reason}")
            
        return True

    def extract_text_from_image(self, image_path):
        """Uses Gemini to extract Hindi text from an image."""
        prompt = "Extract all text from this image and return it as Markdown. Focus on capturing all questions accurately in Hindi."
        
        def _call_image_ocr(model_name):
            with open(image_path, 'rb') as f:
                image_data = f.read()
            mime = 'image/jpeg'
            if image_path.lower().endswith('.png'): mime = 'image/png'
            
            response = client.models.generate_content(
                model=model_name,
                contents=[prompt, types.Part.from_bytes(data=image_data, mime_type=mime)],
                config=GENERATE_CONFIG
            )
            return self._safe_get_text(response)
            
        return self._call_with_model_fallback(_call_image_ocr)

    def extract_image_with_sarvam(self, image_path):
        """Converts an image to a temporary PDF and extracts text using Sarvam AI."""
        try:
            from PIL import Image as PILImage
            sarvam_key = get_fresh_sarvam_key()
            if not sarvam_key:
                raise ValueError("No Sarvam API key found. Falling back to Gemini.")
            sarvam_client = SarvamAI(api_subscription_key=sarvam_key)

            print(f"[Sarvam] Converting image to PDF for OCR: {image_path}")
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_pdf:
                temp_pdf_path = temp_pdf.name

            try:
                img = PILImage.open(image_path).convert("RGB")
                img.save(temp_pdf_path, "PDF")
                print(f"[Sarvam] Image converted to temp PDF: {temp_pdf_path}")
                return self._process_sarvam_job(sarvam_client, temp_pdf_path)
            finally:
                if os.path.exists(temp_pdf_path):
                    os.remove(temp_pdf_path)
        except Exception as e:
            print(f"[Sarvam Image OCR] Failed: {e}. Falling back to Gemini Image OCR...")
            return self.extract_text_from_image(image_path)

    def extract_text_with_gemini(self, pdf_file_path):
        print(f"[Gemini OCR] Uploading PDF to Gemini API: {pdf_file_path}")
        try:
            uploaded_file = client.files.upload(file=pdf_file_path)
            
            # Wait for file to become active
            import time
            for _ in range(30):
                if uploaded_file.state.name == "ACTIVE":
                    break
                elif uploaded_file.state.name == "FAILED":
                    raise ValueError("Gemini file upload failed")
                time.sleep(1)
                uploaded_file = client.files.get(name=uploaded_file.name)
            
            prompt = "Extract all text from this question paper. Return the text exactly as written, preserving all questions in Hindi and English."
            
            model_to_use = self.model_name or 'gemini-2.5-flash'
            print(f"[Gemini OCR] Running OCR with model {model_to_use}...")
            
            response = client.models.generate_content(
                model=model_to_use,
                contents=[uploaded_file, prompt],
                config=GENERATE_CONFIG
            )
            
            # Clean up the file from Gemini storage
            try:
                client.files.delete(name=uploaded_file.name)
            except Exception as delete_err:
                print(f"[Gemini OCR] Cleanup failed: {delete_err}")
                
            text = self._safe_get_text(response)
            if not text:
                raise ValueError("Gemini OCR returned empty text")
            return text
        except Exception as gemini_err:
            print(f"[Gemini OCR] Failed: {gemini_err}")
            # If Gemini fails, fall back to local PyPDF2 text extraction
            return self.extract_text_local_pypdf2(pdf_file_path)

    def extract_text_local_pypdf2(self, pdf_file_path):
        print(f"[Local PDF] Attempting local text extraction with PyPDF2: {pdf_file_path}")
        try:
            import PyPDF2
            with open(pdf_file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                text_parts = []
                for page in reader.pages:
                    text_parts.append(page.extract_text() or "")
                combined_text = "\n".join(text_parts).strip()
                if len(combined_text) > 100:
                    print(f"[Local PDF] Successfully extracted {len(combined_text)} characters locally.")
                    return combined_text
                else:
                    raise ValueError("Extracted text too short, PDF might be scanned/image-only.")
        except Exception as local_err:
            print(f"[Local PDF] Extraction failed: {local_err}")
            raise ValueError("All OCR and PDF text extraction methods failed.")

    def extract_text_with_sarvam(self, pdf_file_path):
        # Try using Sarvam AI first
        try:
            sarvam_key = get_fresh_sarvam_key()
            if not sarvam_key:
                raise ValueError("No Sarvam API key found. Falling back to Gemini OCR.")
                
            import PyPDF2
            sarvam_client = SarvamAI(api_subscription_key=sarvam_key)
            
            with open(pdf_file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                total_pages = len(reader.pages)
                
                if total_pages <= 10:
                    return self._process_sarvam_job(sarvam_client, pdf_file_path)
                    
                print(f"[Sarvam] PDF has {total_pages} pages. Chunking into exactly 2 segments...")
                combined_md = ""
                
                mid_point = total_pages // 2
                chunks = [
                    (0, mid_point),
                    (mid_point, total_pages)
                ]
                
                for start_idx, end_idx in chunks:
                    writer = PyPDF2.PdfWriter()
                    for j in range(start_idx, end_idx):
                        writer.add_page(reader.pages[j])
                        
                    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_pdf:
                        writer.write(temp_pdf)
                        temp_pdf_path = temp_pdf.name
                        
                    try:
                        chunk_text = self._process_sarvam_job(sarvam_client, temp_pdf_path)
                        combined_md += f"\n\n{chunk_text}"
                    finally:
                        if os.path.exists(temp_pdf_path):
                            os.remove(temp_pdf_path)
                            
                return combined_md.strip()
        except Exception as e:
            print(f"[Sarvam] Error occurred: {e}. Falling back to Gemini OCR...")
            return self.extract_text_with_gemini(pdf_file_path)

    def _process_sarvam_job(self, sarvam_client, pdf_path):
        try:
            job = sarvam_client.document_intelligence.create_job(language="hi-IN", output_format="md")
            job.upload_file(pdf_path)
            job.start()
            
            # Custom polling loop with 120s timeout to prevent hanging
            import time
            start_time = time.time()
            timeout = 120
            while True:
                status_obj = job.get_status()
                state = getattr(status_obj, 'job_state', '')
                if not state and isinstance(status_obj, str):
                    state = status_obj
                
                state_lower = str(state).lower()
                
                if state_lower in ["completed", "success"]:
                    break
                elif state_lower == "failed":
                    raise ValueError("Sarvam AI job failed on server.")
                
                if time.time() - start_time > timeout:
                    raise TimeoutError(f"Sarvam AI job timed out after {timeout} seconds.")
                time.sleep(2)

            with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as temp_zip:
                temp_zip_path = temp_zip.name

            try:
                job.download_output(temp_zip_path)
                with zipfile.ZipFile(temp_zip_path, 'r') as z:
                    with z.open('document.md') as f:
                        return f.read().decode('utf-8')
            finally:
                if os.path.exists(temp_zip_path):
                    os.remove(temp_zip_path)

        except socket.gaierror:
            raise ConnectionError(
                "Network Error: Could not connect to Sarvam AI. "
                "Please check your internet connection and try again."
            )
        except Exception as e:
            err_str = str(e)
            # Try to extract only the 'message' field from the Sarvam error body
            try:
                import re
                match = re.search(r"'message':\s*'([^']+)'", err_str)
                if match:
                    raise ValueError(f"Sarvam AI Error: {match.group(1)}")
            except ValueError:
                raise
            except Exception:
                pass
            raise

    def extract_questions_and_summary(self, file_path, subject=None, cached_text=None):
        is_pdf = file_path.lower().endswith('.pdf')
        raw_text = cached_text
        
        if not raw_text:
            if is_pdf:
                print(f"[Pipeline] Extracting text with Sarvam AI (PDF): {file_path}")
                raw_text = self.extract_text_with_sarvam(file_path)
                # Validate extracted text
                self.validate_paper_content(text=raw_text, subject=subject)
            else:
                print(f"[Pipeline] Processing image — validating with Gemini, then OCR via Sarvam AI: {file_path}")
                # Validate using Gemini (visual understanding of image content)
                self.validate_paper_content(image_path=file_path, subject=subject)
                # OCR via Sarvam AI (image converted to temp PDF internally)
                raw_text = self.extract_image_with_sarvam(file_path)
        else:
            print(f"[Pipeline] Using cached OCR text for: {file_path}")
        
        question_instruction = "Extract ALL the questions/topics present in the paper text. Do not limit or omit any; retrieve every single question/topic in Hindi (or in English if the subject is English) so we have a complete list for analysis."
        question_field_desc = "verbatim question text as written in the paper (in English if subject is English, otherwise in Hindi)"
        topic_field_desc = "chapter name (in English if subject is English, otherwise in Hindi)"
        
        prompt = f"""You are an educational study assistant. Analyze this MP Board paper text extracted via OCR.
            
            TASKS:
            1. {question_instruction}
            2. Identify the YEAR of this paper from the document (e.g., 2016 to 2026).
            3. Identify the QUESTION TYPE for each question.
            4. Provide a 3-sentence summary of the paper's difficulty and coverage (write the summary in Hindi).
            
            Question Type must be ONE of these:
            - "लघु उत्तरीय" (Short Answer)
            - "दीर्घ उत्तरीय" (Long Answer)
            - "अति लघु उत्तरीय" (Very Short Answer)
            - "रिक्त स्थान" (Fill in the Blanks)
            - "मिलान करो" (Match the Following)
            - "सत्य/असत्य" (True/False)
            - "बहुविकल्पीय" (Multiple Choice)
            - "आंकिक" (Numerical)
            
            Output ONLY valid JSON in this exact format:
            {{
                "paper_year": "2023",
                "extracted_questions": [
                    {{"question": "{question_field_desc}", "marks": "2 अंक", "topic": "{topic_field_desc}", "year": "2023", "question_type": "लघु उत्तरीय"}}
                ],
                "paper_summary": "3-sentence summary in Hindi"
            }}
            
            IMPORTANT:
            - The "year" field in each question MUST match the paper_year.
            - The "topic" field MUST contain the chapter/topic name.
            - Extract the questions exactly as written (verbatim) in the paper text. Do not paraphrase or change the wording; keep the exact original text.
            
            EXTRACTED PAPER TEXT:
            {raw_text}
            """
        
        def _call_extract(model_name):
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=GENERATE_CONFIG
            )
            text = self._safe_get_text(response)
            if not text:
                raise ValueError("Extraction blocked or empty")
            parsed = self._parse_gemini_json_response(text)
            parsed['raw_text'] = raw_text
            return parsed
        
        return self._call_with_model_fallback(_call_extract)

    def _parse_gemini_json_response(self, text_response):
        cleaned_text = text_response.strip()
        if cleaned_text.startswith("```json"):
            cleaned_text = cleaned_text[7:]
        if cleaned_text.startswith("```"):
            cleaned_text = cleaned_text[3:]
        if cleaned_text.endswith("```"):
            cleaned_text = cleaned_text[:-3]
        return json.loads(cleaned_text.strip())

    def run_gemini_stage_2(self, combined_json_list, num_papers, student_class=None, subject=None):
        data_string = json.dumps(combined_json_list, ensure_ascii=False)
        if num_papers <= 2:
            predicted_count = 15
        elif num_papers == 3:
            predicted_count = 25
        else:
            predicted_count = 40

        syllabus_text = ""
        if student_class == "12th" and subject in CLASS_12_SYLLABUS:
            chapters = "\n".join([f"- {ch}" for ch in CLASS_12_SYLLABUS[subject]])
            syllabus_text = f"\n\n*** IMPORTANT SYLLABUS REFERENCE ***\nFor class 12th {subject}, YOU MUST map every question's 'topic' to ONE of the following official chapters exactly as written:\n{chapters}\n"
        elif student_class == "10th" and subject in CLASS_10_SYLLABUS:
            chapters = "\n".join([f"- {ch}" for ch in CLASS_10_SYLLABUS[subject]])
            syllabus_text = f"\n\n*** IMPORTANT SYLLABUS REFERENCE ***\nFor class 10th {subject}, YOU MUST map every question's 'topic' to ONE of the following official chapters exactly as written:\n{chapters}\n"

        # Extract ONLY the years actually present in the data
        actual_years = sorted(set(
            q.get('year', '') for q in combined_json_list if q.get('year')
        ))
        years_str = ", ".join(actual_years)

        prompt = f"""You are an educational study planner. Analyze ONLY the study topics provided.

            *** STRICT ANTI-HALLUCINATION RULES ***
            - The uploaded papers are ONLY from these years: [{years_str}]
            - You MUST NOT mention any other year in the "years" field. No 2018, 2019, 2020, 2021 unless they are in [{years_str}].
            - Do NOT use your training knowledge to add years. Only use what is in the data below.
            - A "repeated" question/topic is one that appears in MORE than one of the years in [{years_str}].
              You MUST identify and return EVERY single repeated question/topic found in the data below in the "repeated_questions" list. Do not limit, truncate, or omit any repeated questions; return all of them.

            REQUIREMENTS:
            1. Return ALL identified repeated questions/topics in "repeated_questions".
            2. Return EXACTLY {predicted_count} predicted important questions/topics in "predicted_important_questions".
            3. EVERY question MUST have "topic", and "question_type" fields.
            4. For REPEATED questions: "years" must ONLY contain years from [{years_str}] where the question/topic appeared.
            5. For PREDICTED questions: set "year" to "संभावित", and assign a "star_rating" field (integer from 3 to 5, where 5 represents the highest probability of appearing in the next exam, 4 represents high, and 3 represents medium).
            6. Cover ALL chapters and difficulty levels (2 अंक, 3 अंक, 4 अंक, 5 अंक).
            7. "question_type" must be ONE of: "लघु उत्तरीय", "दीर्घ उत्तरीय", "अति लघु उत्तरीय", "रिक्त स्थान", "मिलान करो", "सत्य/असत्य", "बहुविकल्पीय", "आंकिक"{syllabus_text}
            8. For the "question" field of each repeated question, you must use the exact verbatim phrasing from the latest year's paper in which it appeared. Do not paraphrase or genericize it; preserve the exact original wording.

            Output ONLY valid JSON:
            {{
                "repeated_questions": [
                    {{"question": "question in Hindi", "frequency": 2, "years": [{years_str.replace(", ", '", "')}], "marks": "2 अंक", "topic": "chapter", "question_type": "लघु उत्तरीय"}}
                ],
                "predicted_important_questions": [
                    {{"question": "predicted question in Hindi", "marks": "5 अंक", "topic": "chapter", "year": "संभावित", "reason": "why important", "question_type": "दीर्घ उत्तरीय", "star_rating": 5}}
                ]
            }}

            Study Topics Data (papers: {years_str}):
            {data_string}"""
        
        def _call_2(model_name):
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=GENERATE_CONFIG
            )
            text = self._safe_get_text(response)
            if not text:
                raise ValueError("Stage 2 returned empty")
            return self._parse_gemini_json_response(text)
        
        res = self._call_with_model_fallback(_call_2)
        if isinstance(res, dict) and "predicted_important_questions" in res:
            pq = res["predicted_important_questions"]
            if isinstance(pq, list):
                res["predicted_important_questions"] = sorted(
                    pq,
                    key=lambda x: int(x.get("star_rating", 3)) if str(x.get("star_rating", "")).isdigit() else 3,
                    reverse=True
                )
        return res

    def run_gemini_stage_3(self, deduplicated_json, student_class=None, subject=None):
        data_string = json.dumps(deduplicated_json, ensure_ascii=False)
        
        syllabus_text = ""
        if student_class == "12th" and subject in CLASS_12_SYLLABUS:
            chapters = "\n".join([f"- {ch}" for ch in CLASS_12_SYLLABUS[subject]])
            syllabus_text = f"\n\n*** IMPORTANT SYLLABUS REFERENCE ***\nFor class 12th {subject}, YOU MUST use ONLY the following official chapters exactly as written for 'chapter_wise_strategy':\n{chapters}\n"
        elif student_class == "10th" and subject in CLASS_10_SYLLABUS:
            chapters = "\n".join([f"- {ch}" for ch in CLASS_10_SYLLABUS[subject]])
            syllabus_text = f"\n\n*** IMPORTANT SYLLABUS REFERENCE ***\nFor class 10th {subject}, YOU MUST use ONLY the following official chapters exactly as written for 'chapter_wise_strategy':\n{chapters}\n"
            
        prompt = f"""You are an educational strategy advisor. Based on the analyzed study data below,
            provide difficulty analysis and chapter-wise study strategy for students.{syllabus_text}
            
            Output ONLY valid JSON in this exact format:
            {{
                "difficulty_breakdown": {{"easy_questions_count": 5, "medium_questions_count": 10, "hard_questions_count": 3}},
                "pattern_analysis": {{"cyclical_trends": "trend description in Hindi", "emerging_topics": "emerging topics in Hindi"}},
                "chapter_wise_strategy": [
                    {{"chapter_name": "chapter name", "priority_level": "High", "study_tip": "study advice in Hindi"}}
                ],
                "final_student_advice": "overall advice in Hindi"
            }}
            
            Analyzed Study Data:
            {data_string}"""
        
        def _call_3(model_name):
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=GENERATE_CONFIG
            )
            text = self._safe_get_text(response)
            if not text:
                raise ValueError("Stage 3 returned empty")
            return self._parse_gemini_json_response(text)
        
        return self._call_with_model_fallback(_call_3)

    def run_full_pipeline(self, session, exam_papers):
        try:
            # Check cancellation first
            session.refresh_from_db()
            if session.status == 'failed':
                print(f"[Pipeline] Session {session.id} aborted before starting.")
                return
                
            session.status = 'extracting'
            session.save()
            
            combined_extracted_questions = []
            num_papers = len(exam_papers)
            
            print(f"[Pipeline] {num_papers} papers uploaded")
            
            def process_single_paper(paper):
                # Attempt to find cached OCR text and questions from previously processed identical LibraryPaper
                cached_text = None
                cached_questions = None
                if paper.library_paper:
                    previous_paper = ExamPaper.objects.filter(
                        library_paper=paper.library_paper,
                        ocr_raw_text__isnull=False
                    ).exclude(ocr_raw_text="").first()
                    if previous_paper:
                        cached_text = previous_paper.ocr_raw_text
                        print(f"[Pipeline] Found cached OCR text from previous ExamPaper {previous_paper.id} for library paper {paper.library_paper.id}")
                        
                        # Only reuse cached questions if it is not using the legacy 15-question limit
                        if previous_paper.extracted_questions_json and isinstance(previous_paper.extracted_questions_json, list) and len(previous_paper.extracted_questions_json) > 15:
                            cached_questions = previous_paper.extracted_questions_json
                            print(f"[Pipeline] Found cached questions list ({len(cached_questions)} items) from previous ExamPaper {previous_paper.id}")
                
                if cached_questions:
                    paper.ocr_raw_text = cached_text
                    paper.extracted_questions_json = cached_questions
                    paper.save()
                    return cached_questions

                result = self.extract_questions_and_summary(
                    paper.get_file_path(), 
                    subject=session.subject, 
                    cached_text=cached_text
                )
                extracted_qs = result.get("extracted_questions", [])
                
                paper.ocr_raw_text = result.get("raw_text", result.get("paper_summary", "Summary extracted."))
                paper.extracted_questions_json = extracted_qs
                paper.save()
                return extracted_qs

            print(f"[Pipeline] Processing {num_papers} papers sequentially to avoid API quota overlap...")
            for paper in exam_papers:
                try:
                    # Check cancellation before processing each paper
                    session.refresh_from_db()
                    if session.status == 'failed':
                        print(f"[Pipeline] Session {session.id} aborted during paper loop.")
                        return
                        
                    questions = process_single_paper(paper)
                    combined_extracted_questions.extend(questions)
                    # Small delay between papers to let the API breathe
                    time.sleep(2)
                except Exception as e:
                    print(f"Error processing paper {paper.id}: {e}")
                    raise e

            # Check cancellation before Stage 2
            session.refresh_from_db()
            if session.status == 'failed':
                print(f"[Pipeline] Session {session.id} aborted before Stage 2.")
                return

            session.status = 'analyzing'
            session.save()

            stage_2_result = self.run_gemini_stage_2(
                combined_extracted_questions, 
                num_papers, 
                session.student_class, 
                session.subject
            )

            # Check cancellation before Stage 3
            session.refresh_from_db()
            if session.status == 'failed':
                print(f"[Pipeline] Session {session.id} aborted before Stage 3.")
                return

            stage_3_result = self.run_gemini_stage_3(
                stage_2_result, 
                session.student_class, 
                session.subject
            )

            return {"stage_2": stage_2_result, "stage_3": stage_3_result}
            
        except Exception as e:
            # Log the error for debugging
            with open(os.path.join(settings.BASE_DIR, "error_log.txt"), "a") as f:
                import traceback
                f.write(f"\n[Pipeline Crash] {time.ctime()}:\n")
                f.write(traceback.format_exc())
            print(f"Pipeline crashed: {e}")
            raise e
