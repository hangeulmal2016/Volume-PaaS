// Thay đường dẫn này bằng link thực tế sau khi bạn Deploy Backend lên Koyeb thành công
const API_URL = "https://koyeb.app"; 
let calculatedGridData = [];
let currentGridSize = 5;

function toggleMode(prefix) {
    const mode = document.getElementById(`${prefix}_mode`).value;
    document.getElementById(`file_${prefix}`).classList.toggle('hidden', mode !== 'file');
    document.getElementById(`fixed_${prefix}`).classList.toggle('hidden', mode !== 'fixed');
}

// Tự động đọc preview khi chọn file trên điện thoại
document.getElementById('file_bm1').addEventListener('change', (e) => handleFilePreview(e.target.files[0], 'preview_bm1'));
document.getElementById('file_bm2').addEventListener('change', (e) => handleFilePreview(e.target.files[0], 'preview_bm2'));

async function handleFilePreview(file, previewId) {
    if (!file) return;
    let formData = new FormData();
    formData.append("file", file);
    try {
        let res = await fetch(`${API_URL}/api/preview-txt`, { method: "POST", body: formData });
        let data = await res.json();
        let box = document.getElementById(previewId);
        box.classList.remove('hidden');
        box.innerText = "5 dòng đầu tiên đọc được:\n" + data.preview.map(line => line.join(" | ")).join("\n");
    } catch (err) { alert("Lỗi kết nối hoặc định dạng file không đúng."); }
}

async function runCalculation() {
    const btn = document.getElementById('btn_calc');
    btn.innerText = "🔄 ĐANG TÍNH TOÁN...";
    btn.disabled = true;

    let formData = new FormData();
    formData.append("grid_size", document.getElementById('grid_size').value);

    if (document.getElementById('bm1_mode').value === 'file') {
        formData.append("file_bm1", document.getElementById('file_bm1').files[0]);
    } else {
        formData.append("bm1_fixed_z", document.getElementById('fixed_bm1').value);
    }

    if (document.getElementById('bm2_mode').value === 'file') {
        formData.append("file_bm2", document.getElementById('file_bm2').files[0]);
    } else {
        formData.append("bm2_fixed_z", document.getElementById('fixed_bm2').value);
    }

    try {
        let res = await fetch(`${API_URL}/api/calculate`, { method: "POST", body: formData });
        if (!res.ok) { let err = await res.json(); throw new Error(err.detail); }
        let data = await res.json();
        
        calculatedGridData = data.grid_data;
        currentGridSize = data.grid_size;

        document.getElementById('res_cut').innerText = data.summary.cut.toLocaleString();
        document.getElementById('res_fill').innerText = data.summary.fill.toLocaleString();
        document.getElementById('res_net').innerText = data.summary.net.toLocaleString();
        document.getElementById('res_cells').innerText = data.summary.cells.toLocaleString();
        document.getElementById('result_card').classList.remove('hidden');
        
        // Cuộn màn hình xuống vùng kết quả để kỹ sư thấy ngay trên màn hình điện thoại
        document.getElementById('result_card').scrollIntoView({ behavior: 'smooth' });
    } catch (err) {
        alert("Lỗi: " + err.message);
    } finally {
        btn.innerText = "⚡ TÍNH KHỐI LƯỢNG";
        btn.disabled = false;
    }
}

async function downloadFile(type) {
    let url = `${API_URL}/api/export/${type}`;
    let body = type === 'excel' ? JSON.stringify(calculatedGridData) : JSON.stringify({ grid_data: calculatedGridData, grid_size: currentGridSize });
    
    try {
        let res = await fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: body
        });
        let blob = await res.blob();
        let link = document.createElement('a');
        link.href = window.URL.createObjectURL(blob);
        link.download = type === 'excel' ? "bao_cao_khoi_luong.xlsx" : "ban_ve_luoi.dxf";
        link.click();
    } catch (err) { alert("Lỗi khi xuất và tải file."); }
}
