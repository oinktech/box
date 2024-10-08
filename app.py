from flask import Flask, render_template, request, redirect, url_for, flash, send_file
import lzma
import os
import struct
from io import BytesIO

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# 壓縮邏輯
def create_box(files):
    compressed_data = BytesIO()
    
    # 保持 BytesIO 開放狀態，寫入所有數據
    num_files = len(files)
    compressed_data.write(struct.pack('I', num_files))  # 寫入文件數量
    
    for file in files:
        filename = file.filename
        file_data = file.read()  # 讀取文件數據
        compressed = lzma.compress(file_data)  # 壓縮文件數據
        
        # 寫入文件名和壓縮數據
        compressed_data.write(struct.pack('I', len(filename)))  # 文件名長度
        compressed_data.write(filename.encode('utf-8'))  # 文件名
        compressed_data.write(struct.pack('I', len(compressed)))  # 壓縮數據長度
        compressed_data.write(compressed)  # 壓縮數據
    
    compressed_data.seek(0)  # 重置讀取指針
    return compressed_data

# 解壓縮邏輯
def extract_box(file):
    extracted_files = []
    
    # 使用 with 語句確保檔案正確處理
    with file.stream as f:
        num_files = struct.unpack('I', f.read(4))[0]  # 讀取文件數量
        for _ in range(num_files):
            filename_length = struct.unpack('I', f.read(4))[0]  # 讀取文件名長度
            filename = f.read(filename_length).decode('utf-8')  # 讀取文件名
            compressed_size = struct.unpack('I', f.read(4))[0]  # 讀取壓縮數據長度
            compressed_data = f.read(compressed_size)  # 讀取壓縮數據
            decompressed_data = lzma.decompress(compressed_data)  # 解壓縮數據
            
            extracted_files.append((filename, decompressed_data))  # 存儲解壓縮的文件
    return extracted_files

# 壓縮頁面
@app.route('/')
def index():
    return render_template('index.html')

# 解壓縮頁面
@app.route('/decompress')
def decompress_page():
    return render_template('decompress.html')

# 比較頁面
@app.route('/compare')
def compare_page():
    return render_template('compare.html')

# 處理壓縮請求
@app.route('/upload', methods=['POST'])
def upload_files():
    if 'file' not in request.files:
        flash('未選擇任何文件！')
        return redirect(request.url)
    
    files = request.files.getlist('file')
    if not files:
        flash('請選擇文件進行壓縮！')
        return redirect(request.url)
    
    try:
        first_filename = os.path.splitext(files[0].filename)[0]
        
        compressed_data = create_box(files)  # 創建 .box 文件
        box_filename = f"{first_filename}.box"  # 生成 .box 文件名
        
        return send_file(compressed_data, as_attachment=True, download_name=box_filename)
    except Exception as e:
        flash(f'壓縮過程中出錯：{str(e)}')
        return redirect(url_for('index'))

# 處理解壓縮請求
@app.route('/extract', methods=['POST'])
def extract_files():
    if 'file' not in request.files:
        flash('未選擇任何文件！')
        return redirect(request.url)
    
    file = request.files['file']
    try:
        extracted_files = extract_box(file)  # 解壓縮 .box 文件
        return render_template('extracted.html', files=extracted_files)  # 顯示解壓縮的文件
    except Exception as e:
        flash(f'解壓縮過程中出錯：{str(e)}')
        return redirect(url_for('decompress_page'))

# 處理比較請求
@app.route('/compare/upload', methods=['POST'])
def compare_files():
    if 'file' not in request.files:
        flash('未選擇任何文件！')
        return redirect(request.url)

    files = request.files.getlist('file')
    if not files:
        flash('請選擇文件進行比較！')
        return redirect(request.url)

    try:
        # 計算 .box 的大小
        box_data = create_box(files)  # 創建 .box 文件
        box_size = len(box_data.getvalue())  # 獲取 .box 文件大小

        return render_template('comparison_result.html', box_size=box_size)  # 顯示比較結果
    except Exception as e:
        flash(f'比較過程中出錯：{str(e)}')
        return redirect(url_for('compare_page'))

if __name__ == '__main__':
    app.run(debug=True,port=10000, host='0.0.0.0')
