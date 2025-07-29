from flask import Flask, request, jsonify
import pdfplumber, requests, re, os
from io import BytesIO
import openai

app = Flask(__name__)

# ✅ Configure OpenAI
openai.api_key = os.environ.get("OPENAI_API_KEY")

# ✅ Health Check Route
@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "PDF Parser Service is running ✅"})

@app.route('/parse', methods=['POST'])
def parse_pdf():
    data = request.get_json()
    file_url = data.get("fileUrl")
    if not file_url:
        return jsonify({"error": "fileUrl missing"}), 400

    # Step 1: Download the PDF
    try:
        resp = requests.get(file_url, timeout=30)
        resp.raise_for_status()
    except Exception as e:
        print(f"[ERROR] File download failed: {e}", flush=True)
        return jsonify({"error": f"File download failed: {str(e)}"}), 500

    transactions = []
    # Regex pattern to capture [date] [description] [amount]
    line_pattern = re.compile(
        r'(\d{2}/\d{2}/\d{4})\s+(.+?)\s+([-+]?\d+[.,]\d{2})'
    )

    # Step 2: Parse PDF safely
    try:
        with pdfplumber.open(BytesIO(resp.content)) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                for line in text.splitlines():
                    # Keep only lines that likely contain monetary values
                    if any(currency in line for currency in ["£", "€", "$"]):
                        match = line_pattern.search(line)
                        if match:
                            date, description, amount = match.groups()
                            amount = amount.replace(',', '.')
                            transactions.append({
                                "date": date,
                                "description": description.strip(),
                                "amount": float(amount),
                                "raw_line": line
                            })
                        else:
                            # fallback if regex doesn't match
                            transactions.append({"raw_line": line})

        # Step 3: Generate AI financial summary
        summary_text = None
        if openai.api_key and transactions:
            try:
                prompt = (
                    "You are a helpful financial assistant. Analyze these transactions and provide:\n"
                    "1. A 2-sentence summary of spending trends.\n"
                    "2. Three actionable suggestions to improve finances.\n"
                    "3. One reflection question.\n\n"
                    f"Transactions: {transactions}"
                )

                response = openai.ChatCompletion.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "You are a financial analyst."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=300,
                    temperature=0.7
                )
                summary_text = response.choices[0].message.content
            except Exception as e:
                print(f"[ERROR] OpenAI summarization failed: {e}", flush=True)

        return jsonify({
            "transactions": transactions,
            "summary": summary_text or "AI summary unavailable"
        })

    except Exception as e:
        print(f"[ERROR] PDF parsing failed: {e}", flush=True)
        return jsonify({"error": f"PDF parsing failed: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
