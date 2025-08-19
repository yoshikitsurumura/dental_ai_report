from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.templating import Jinja2Templates
import uvicorn
import os
from pathlib import Path
import shutil
import json
from typing import Optional

# Gemini APIと環境変数、画像処理のためのインポート
import google.generativeai as genai
from dotenv import load_dotenv
from PIL import Image

# reportlab のインポート
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.lib.utils import ImageReader
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib import colors
import markdown

app = FastAPI()

# .env ファイルから環境変数を読み込む
load_dotenv()
# Gemini APIキーを設定
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# このファイルの場所を基準に絶対パスを構築
BASE_DIR = Path(__file__).resolve().parent

# 日本語フォントの登録
FONT_PATH = Path(BASE_DIR, "fonts", "ipaexg.ttf")
if FONT_PATH.exists():
    pdfmetrics.registerFont(TTFont('IPAexGothic', str(FONT_PATH)))
    pdfmetrics.registerFontFamily('IPAexGothic', normal='IPAexGothic', bold='IPAexGothic', italic='IPAexGothic', boldItalic='IPAexGothic')
else:
    print(f"Warning: Japanese font not found at {FONT_PATH}. Please place IPAexGothic.ttf in the 'fonts' directory.")

# templatesディレクトリの絶対パスを設定
templates = Jinja2Templates(directory=str(Path(BASE_DIR, "templates")))

# アップロードされたファイルを保存するディレクトリも絶対パスで設定
UPLOAD_DIR = Path(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    # index.htmlをレンダリングして返す
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/diagnose", response_class=FileResponse)
async def diagnose(
    # 患者基本情報
    patient_name: str = Form(...),
    patient_age: int = Form(...),
    birth_date: str = Form(...),
    gender: str = Form(...),
    guardian_name: str = Form(...),
    phone_number: str = Form(...),
    email: str = Form(...),
    chief_complaint: str = Form(...),
    medical_history: str = Form(...),

    # 問診項目
    mouth_breathing: str = Form(...),
    thumb_sucking: str = Form(...),
    nail_biting: str = Form(...),
    tongue_thrust: str = Form(...),
    snoring: str = Form(...),
    tonsil_swelling: str = Form(...),
    allergic_rhinitis: str = Form(...),
    eating_sounds: str = Form(...),
    swallowing_pattern: str = Form(...),

    # 口腔内検査項目
    upper_jaw_condition: str = Form(...),
    lower_jaw_condition: str = Form(...),
    midline_deviation: float = Form(...),
    crossbite: str = Form(...),
    tongue_position: str = Form(...),
    lip_closure: str = Form(...),
    facial_appearance: str = Form(...),
    tmd_symptoms: str = Form(...),
    other_findings: str = Form(...),

    # 口腔内写真アップロード
    oral_photo_front: Optional[UploadFile] = File(None),
    oral_photo_upper_occlusal: Optional[UploadFile] = File(None),
    oral_photo_lower_occlusal: Optional[UploadFile] = File(None),
    oral_photo_right_lateral: Optional[UploadFile] = File(None),
    oral_photo_left_lateral: Optional[UploadFile] = File(None)
):
    """
    フォームデータを受け取り、診断ロジックを実行し、
    結果をPDFレポートで返すエンドポイント。
    """
    # 1. ダミーAI分析ロジック (一旦削除)
    # 2. 診断ロジックの実装
    # 2.1. スコア計算ロジック
    # 筋機能評価スコア (MFS)
    mfs_score = 0
    mfs_items = [mouth_breathing, thumb_sucking, nail_biting, tongue_thrust, snoring, tonsil_swelling, allergic_rhinitis, eating_sounds, swallowing_pattern]
    mfs_yes_items = []
    for item_name, item_value in zip(["口呼吸", "指しゃぶり", "爪噛み", "舌癖", "いびき", "扁桃腺の腫れ", "アレルギー性鼻炎", "食事中の音", "嚥下パターン"], mfs_items):
        if item_value == 'yes':
            mfs_score += 1
            mfs_yes_items.append(item_name)

    # 歯列評価スコア (DAS)
    das_score = 0
    das_items = []
    if upper_jaw_condition == 'crowding':
        das_score += 3
        das_items.append("上顎の叢生")
    elif upper_jaw_condition == 'spacing':
        das_score += 1
        das_items.append("上顎の空隙歯列")

    if lower_jaw_condition == 'crowding':
        das_score += 3
        das_items.append("下顎の叢生")
    elif lower_jaw_condition == 'spacing':
        das_score += 1
        das_items.append("下顎の空隙歯列")

    if midline_deviation >= 1.0:
        das_score += 1
        das_items.append(f"正中線のずれ ({midline_deviation}mm)")

    if crossbite == 'yes':
        das_score += 2
        das_items.append("交叉咬合")

    # 2.2. リスク判定ロジック
    risk_level = "低リスク"
    if mouth_breathing == 'yes' and tongue_thrust == 'yes' and (upper_jaw_condition == 'crowding' or lower_jaw_condition == 'crowding'):
        risk_level = "高リスク"
    elif mouth_breathing == 'yes' or tongue_thrust == 'yes':
        risk_level = "中リスク"

    # 2.3. アプライアンス選択ロジック
    appliance_suggestion = "要相談"
    if 6 <= patient_age <= 10 and upper_jaw_condition == 'crowding':
        appliance_suggestion = "T4K"
    elif 3 <= patient_age <= 5:
        appliance_suggestion = "Myobrace for Juniors"
    
    # 仮の診断結果を作成
    diagnosis_result = {
        "patient_info": {
            "name": patient_name,
            "age": patient_age,
        },
        "analysis_summary": {
            "risk_level": risk_level,
            "appliance_suggestion": appliance_suggestion,
            "mfs_score": mfs_score,
            "das_score": das_score,
            "mfs_yes_items": mfs_yes_items,
            "das_items": das_items,
            "comments": [f"MFSスコア: {mfs_score}/9", f"DASスコア: {das_score}/9"],
        }
    }
    diagnosis_result['other_findings'] = other_findings
    
    # 2. アップロードされた写真の処理 (複数枚対応)
    photo_paths = []
    gemini_analyses = []
    
    # アップロードされた可能性のある全ての写真を確認
    uploaded_photos = {
        "正面観": oral_photo_front,
        "上顎咬合面観": oral_photo_upper_occlusal,
        "下顎咬合面観": oral_photo_lower_occlusal,
        "右側方観": oral_photo_right_lateral,
        "左側方観": oral_photo_left_lateral,
    }

    for view_name, oral_photo in uploaded_photos.items():
        if oral_photo and oral_photo.filename:
            # 写真を保存
            photo_path = UPLOAD_DIR / oral_photo.filename
            with photo_path.open("wb") as buffer:
                shutil.copyfileobj(oral_photo.file, buffer)

            # Gemini Vision APIによる画像解析
            try:
                img = Image.open(photo_path)
                model = genai.GenerativeModel('models/gemini-1.5-flash')
                prompt = f"""この{view_name}の口腔内写真について、歯科医の視点から詳細に分析してください。
                分析結果はMarkdown形式で、箇条書きなどを用いて分かりやすく記述してください。"""
                response = model.generate_content([prompt, img])
                
                gemini_analysis = response.text
                gemini_analyses.append({"view": view_name, "analysis": gemini_analysis})
                photo_paths.append({"view": view_name, "path": str(photo_path)})

                print(f"Gemini AI Analysis for {view_name}: {gemini_analysis}")

            except Exception as e:
                print(f"Gemini Vision API呼び出し中にエラーが発生しました ({view_name}): {e}")
                gemini_analyses.append({"view": view_name, "analysis": f"AI画像解析中にエラーが発生しました: {e}"})

    diagnosis_result["gemini_analyses"] = gemini_analyses
    diagnosis_result["photo_paths"] = photo_paths


    # 4. PDFレポートの生成
    try:
        pdf_filename = f"diagnosis_report_{patient_name}_{patient_age}.pdf"
        pdf_path = UPLOAD_DIR / pdf_filename
        
        c = canvas.Canvas(str(pdf_path), pagesize=letter)
        
        # ==================================================================
        # 術者向けAI診断サマリー (1ページ目)
        # ==================================================================
        create_summary_page(c, diagnosis_result)

        # ==================================================================
        # 保護者向けカウンセリングレポート (2ページ目以降)
        # ==================================================================
        c.showPage() # 改ページ
        create_counseling_report_page(c, diagnosis_result, photo_paths, gemini_analyses)

        c.save()

        return FileResponse(path=pdf_path, media_type="application/pdf", filename=pdf_filename)

    except Exception as e:
        print(f"Error during PDF generation: {e}")
        return JSONResponse(status_code=500, content={"message": f"PDF生成中にエラーが発生しました: {e}"})

def create_summary_page(c, diagnosis_result):
    """術者向けAI診断サマリーページを作成する"""
    width, height = letter
    styles = getSampleStyleSheet()
    
    # スタイルの設定
    styleH1 = ParagraphStyle(name='H1', fontName='IPAexGothic', fontSize=16, leading=22, alignment=TA_CENTER)
    styleH2 = ParagraphStyle(name='H2', fontName='IPAexGothic', fontSize=12, leading=18)
    styleT = ParagraphStyle(name='Table', fontName='IPAexGothic', fontSize=10, leading=14)
    styleBody = ParagraphStyle(name='Body', fontName='IPAexGothic', fontSize=10, leading=14)

    # タイトル
    p = Paragraph("術者向けAI診断サマリー", styleH1)
    p.wrapOn(c, width - 2 * inch, height)
    p.drawOn(c, 1 * inch, height - 1 * inch)

    # 患者情報テーブル
    patient_info = diagnosis_result['patient_info']
    summary_data = diagnosis_result['analysis_summary']
    
    data = [
        [Paragraph('<b>患者氏名</b>', styleT), Paragraph(patient_info['name'], styleT), Paragraph('<b>年齢</b>', styleT), Paragraph(str(patient_info['age']), styleT)],
        [Paragraph('<b>リスク判定</b>', styleT), Paragraph(f'<b>{summary_data["risk_level"]}</b>', styleT), Paragraph('<b>推奨アプライアンス</b>', styleT), Paragraph(summary_data["appliance_suggestion"], styleT)],
        [Paragraph('<b>筋機能評価スコア (MFS)</b>', styleT), Paragraph(f'<b>{summary_data["mfs_score"]} / 9</b>', styleT), Paragraph('<b>歯列評価スコア (DAS)</b>', styleT), Paragraph(f'<b>{summary_data["das_score"]} / 9</b>', styleT)],
    ]
    
    table = Table(data, colWidths=[1.5*inch, 2*inch, 1.7*inch, 2.3*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('BACKGROUND', (2, 0), (2, -1), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]))
    
    table.wrapOn(c, width - 2 * inch, height)
    table.drawOn(c, 1 * inch, height - 2.5 * inch)

    # AIによる口腔内写真の客観的所見
    y_pos = height - 3.5 * inch
    p = Paragraph("<b>【AIによる口腔内写真の客観的所見】</b>", styleH2)
    p.wrapOn(c, width - 2 * inch, height)
    p.drawOn(c, 1 * inch, y_pos)
    y_pos -= 0.4 * inch
    
    gemini_analyses = diagnosis_result.get("gemini_analyses", [])
    if gemini_analyses:
        for analysis in gemini_analyses:
            # MarkdownをHTMLに変換してParagraphで描画
            html_text = markdown.markdown(f"<b>{analysis['view']}:</b> {analysis['analysis']}")
            p = Paragraph(html_text, styleBody)
            p_height = p.wrap(width - 2.2 * inch, height)[1]
            if y_pos - p_height < 1 * inch:
                c.showPage()
                y_pos = height - 1 * inch
            p.drawOn(c, 1.1 * inch, y_pos - p_height)
            y_pos -= p_height + 10
    else:
        p = Paragraph("口腔内写真の解析結果はありません。", styleBody)
        p.wrapOn(c, width - 2.2 * inch, height)
        p.drawOn(c, 1.1 * inch, y_pos - 0.2 * inch)
        y_pos -= 0.4 * inch

    # 特記事項
    y_pos -= 0.4 * inch
    p = Paragraph("<b>【特記事項】</b>", styleH2)
    p.wrapOn(c, width - 2 * inch, height)
    p.drawOn(c, 1 * inch, y_pos)
    y_pos -= 0.4 * inch

    # (MFSとDASの詳細項目などをここに記載)
    p = Paragraph(f"<b>MFS項目 ({summary_data['mfs_score']}点):</b> {', '.join(summary_data['mfs_yes_items'])}", styleBody)
    p.wrapOn(c, width - 2.2 * inch, height)
    p.drawOn(c, 1.1 * inch, y_pos - p.height)
    y_pos -= p.height + 10

    p = Paragraph(f"<b>DAS項目 ({summary_data['das_score']}点):</b> {', '.join(summary_data['das_items'])}", styleBody)
    p.wrapOn(c, width - 2.2 * inch, height)
    p.drawOn(c, 1.1 * inch, y_pos - p.height)
    y_pos -= p.height + 10
    
    # その他所見
    if diagnosis_result.get('other_findings'):
        p = Paragraph(f"<b>その他口腔内所見:</b> {diagnosis_result['other_findings']}", styleBody)
        p.wrapOn(c, width - 2.2 * inch, height)
        p.drawOn(c, 1.1 * inch, y_pos - p.height)

def create_counseling_report_page(c, diagnosis_result, photo_paths, gemini_analyses):
    """保護者向けカウンセリングレポートページを作成する"""
    width, height = letter
    styles = getSampleStyleSheet()
    
    # スタイルの設定
    styleH1 = ParagraphStyle(name='H1', fontName='IPAexGothic', fontSize=18, leading=24, alignment=TA_CENTER, spaceAfter=20)
    styleH2 = ParagraphStyle(name='H2', fontName='IPAexGothic', fontSize=14, leading=18, spaceBefore=15, spaceAfter=10)
    styleBody = ParagraphStyle(name='Body', fontName='IPAexGothic', fontSize=11, leading=16)
    
    patient_name = diagnosis_result['patient_info']['name']
    summary_data = diagnosis_result['analysis_summary']
    mfs_score = summary_data['mfs_score']

    # 掴み
    p = Paragraph(f"<b>{patient_name}くん・ちゃんの健やかな成長のために</b><br/><b>大切なお口のお話</b>", styleH1)
    p.wrapOn(c, width - 2 * inch, height)
    p.drawOn(c, 1 * inch, height - 1.5 * inch)

    y_pos = height - 2.5 * inch

    # 現状の説明
    p = Paragraph("<b>【いま、お口の中で起きていること】</b>", styleH2)
    p.wrapOn(c, width - 2 * inch, height)
    p.drawOn(c, 1 * inch, y_pos)
    y_pos -= p.height + 10

    p = Paragraph(f"お口の悪い癖が、<b>{mfs_score}個</b>も見つかりました。<br/>このままだと、将来の歯並びだけでなく、健康にも影響が出てしまうかもしれません。", styleBody)
    p.wrapOn(c, width - 2 * inch, height)
    p.drawOn(c, 1 * inch, y_pos - p.height)
    y_pos -= p.height + 20
    
    # (口腔内写真とAIの指摘を表示するロジック)
    # ここでは最初の写真と解析結果を表示する例
    if photo_paths and gemini_analyses:
        photo_info = photo_paths[0]
        analysis_info = gemini_analyses[0]
        
        try:
            # 画像を描画
            img_path = photo_info['path']
            img = ImageReader(img_path)
            img_width, img_height = img.getSize()
            aspect = img_height / float(img_width)
            draw_width = 3 * inch
            draw_height = draw_width * aspect
            c.drawImage(img, 1.5 * inch, y_pos - draw_height, width=draw_width, height=draw_height)
            y_pos -= draw_height + 10

            # AIの分析結果を描画
            p = Paragraph(f"AI（人工知能）の分析でも、<b>この部分</b>（写真参照）が、将来問題になる可能性があると指摘されています。", styleBody)
            p.wrapOn(c, width - 2 * inch, height)
            p.drawOn(c, 1 * inch, y_pos - p.height)
            y_pos -= p.height + 20

        except Exception as e:
            print(f"Error embedding counseling image: {e}")


    # 原因の説明
    p = Paragraph("<b>【なぜ、そうなってしまったの？】</b>", styleH2)
    p.wrapOn(c, width - 2 * inch, height)
    p.drawOn(c, 1 * inch, y_pos - p.height)
    y_pos -= p.height + 10

    p = Paragraph("実は、これらの問題の根本的な原因は、<b>「口呼吸」</b>や<b>「舌の悪い癖」</b>にあるのです。<br/>（ここに口呼吸や舌癖を説明するイラストを挿入）", styleBody)
    p.wrapOn(c, width - 2 * inch, height)
    p.drawOn(c, 1 * inch, y_pos - p.height)
    y_pos -= p.height + 20

    # 解決策の提示
    appliance = summary_data['appliance_suggestion']
    p = Paragraph("<b>【未来のための解決策があります】</b>", styleH2)
    p.wrapOn(c, width - 2 * inch, height)
    p.drawOn(c, 1 * inch, y_pos - p.height)
    y_pos -= p.height + 10

    p = Paragraph(f"そこで、当院では<b>「MRC治療」</b>をお勧めしています。<br/>これは、<b>「{appliance}」</b>という、柔らかいマウスピース型の装置を使って、お口の悪い癖を治し、あごの成長を助け、歯並びを自然に整える、世界中で行われている治療法です。", styleBody)
    p.wrapOn(c, width - 2 * inch, height)
    p.drawOn(c, 1 * inch, y_pos - p.height)
    y_pos -= p.height + 20

    # 未来の提示 & クロージング
    p = Paragraph("<b>【MRC治療で得られる素晴らしい未来】</b>", styleH2)
    p.wrapOn(c, width - 2 * inch, height)
    p.drawOn(c, 1 * inch, y_pos - p.height)
    y_pos -= p.height + 10
    
    p = Paragraph("<b>綺麗な歯並び</b>と、<b>健康的な体</b>を手に入れることができます。<br/>正しい呼吸は、集中力アップや、運動能力の向上にも繋がります。<br/><br/>より詳しいお話にご興味があれば、ぜひ一度ご相談ください。<br/>専門のスタッフが、丁寧にご説明させていただきます。", styleBody)
    p.wrapOn(c, width - 2 * inch, height)
    p.drawOn(c, 1 * inch, y_pos - p.height)