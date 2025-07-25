function hello() {
    alert("你好！這是來自 static/main.js 的訊息！");
}

function toggleSidebar() {
    var sidebar = document.getElementById('sidebar');
    var container = document.getElementById('container');
    sidebar.classList.toggle('collapsed');
    container.classList.toggle('sidebar-collapsed');
}

// 這裡可以用台股、個人常用股票都行
const stocks = [
    "2330 台積電",
    "2317 鴻海",
    "2454 聯發科",
    "2303 聯電",
    "1301 台塑",
    "1101 台泥"
];

function add_stock() {
    // 先fetch stocks 資料
    // 這裡假設你有一個 API 可以取得股票列表
    
    let stocks = [];
    fetch('/get_stocks_names')
    .then(response => response.json())
    .then(data => {
        // 假設 data 是一個股票名稱的陣列
        if (data && Array.isArray(data)) {
            stocks = data;
        } else {
            Swal.fire('錯誤', '無法取得股票資料', 'error');
        }
    })



    // 建立下拉選單 HTML 字串
    let selectHtml = `<select id="swal-stock-select" style="width:100%">
        <option></option>
        ${stocks.map(s => `<option value="${s}">${s}</option>`).join('')}
    </select>`;

    // 用 SweetAlert2 彈窗
    Swal.fire({
        title: '請選擇要新增的股票',
        html: selectHtml,
        showCancelButton: true,
        confirmButtonText: '確認',
        cancelButtonText: '取消',
        didOpen: () => {
            // 初始化 select2
            $('#swal-stock-select').select2({
                dropdownParent: $('.swal2-popup'),
                placeholder: '請輸入/選擇股票',
                allowClear: true
            });
        },
        preConfirm: () => {
            const selected = $('#swal-stock-select').val();
            if (!selected) {
                Swal.showValidationMessage('請選擇一個股票');
            }
            return selected;
        }
    }).then((result) => {
        if (result.isConfirmed && result.value) {
            // 這裡 result.value 就是你選到的股票
            // 你可以拿去送 API 或直接用
            alert('你選擇了：' + result.value);
        }
    });
}


