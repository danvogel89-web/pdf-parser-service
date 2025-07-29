from flask import Flask, request, jsonify
import pdfplumber
import requests
from io import BytesIO

app = Flask(__name__)

@app.route('/parse', methods=['POST'])
def parse_pdf():
    data = request.get_json()
    file_url = data.get("fileUrl")
    if not file_url:
        return jsonify({"error": "fileUrl missing"}), 400

    try:
        resp = requests.get(file_url)
        resp.raise_for_status()

        transactions = []
        with pdfplumber.open(BytesIO(resp.content)) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                lines = text.split("\n")

                i = 0
                while i < len(lines):
                    line = lines[i]
                    if "Fecha de valor" in line and i + 1 < len(lines):
                        description_lines = []
                        j = i - 1
                        while j >= 0 and not any(
                            kw in lines[j] for kw in
                            ["Fecha", "Descripción", "Extracto", "Emitido en", "Resumen"]
                        ):
                            description_lines.insert(0, lines[j])
                            j -= 1

                        description = " ".join(description_lines).strip()
                        amount_line = lines[i + 1]
                        date, amount = None, None
                        try:
                            date_part, amount_part = amount_line.strip().rsplit(" ", 1)
                            date = date_part.strip()
                            clean_amount = amount_part.replace("€", "").replace(",", ".").replace("+", "").replace("-", "").strip()
                            amount = float(clean_amount)
                            if "-" in amount_part:
                                amount = -amount
                        except:
                            pass

                        if description and date and amount is not None:
                            transactions.append({
                                "date": date,
                                "description": description,
                                "amount": round(amount, 2)
                            })
                        i += 2
                    else:
                        i += 1

        return jsonify({"transactions": transactions})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
