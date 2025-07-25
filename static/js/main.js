function toggleSidebar() {
    var sidebar = document.getElementById('sidebar');
    sidebar.classList.toggle('open');
}



function add_stock() {
    Swal.fire({
        title: '請輸入/選擇股票',
        html: '<select id="swal-stock-select" style="width:100%"></select>',
        showCancelButton: true,
        confirmButtonText: '確認',
        cancelButtonText: '取消',
        didOpen: () => {
            $('#swal-stock-select').select2({
                dropdownParent: $('.swal2-popup'),
                placeholder: '請輸入/選擇股票（支援代號/名稱模糊搜尋）',
                minimumInputLength: 0,
                allowClear: true,
                ajax: {
                    url: '/search_stocks',
                    dataType: 'json',
                    delay: 250,
                    data: function (params) {
                        return { q: params.term };
                    },
                    processResults: function (data) {
                        return {
                            results: data.map(s => ({
                                id: s['證券代號'],
                                text: s['證券代號'] + ' ' + s['證券名稱']
                            }))
                        };
                    },
                    cache: true
                }
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
            // 重新撈一次完整股票資訊
            fetch(`/search_stocks?q=${result.value}`)
                .then(response => response.json())
                .then(data => {
                    const chosen = data.find(s => s['證券代號'] === result.value);
                    if (chosen) {
                        fetch('/add_stock', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                "證券代號": chosen['證券代號'],
                                "證券名稱": chosen['證券名稱']
                            })
                        })
                        .then(r => r.json())
                        .then(rdata => {
                            if (rdata.status === 'ok') {
                                Swal.fire('成功', '已新增股票！', 'success').then(() => {
                                    load_user_stocks();
                                });
                            } else {
                                Swal.fire('錯誤', rdata.msg || '新增失敗', 'error');
                            }
                        })
                        .catch(e => {
                            Swal.fire('錯誤', 'API 發送失敗', 'error');
                        });
                    } else {
                        Swal.fire('錯誤', '找不到股票資訊', 'error');
                    }
                });
        }
    });
}

function load_user_stocks() {
    fetch('/get_user_stocks')
        .then(r => r.json())
        .then(data => {
            const container = document.getElementById('stock-btns');
            container.innerHTML = '';
            if (Array.isArray(data)) {
                data.forEach(s => {
                    const btn = document.createElement('button');
                    btn.className = 'stock-btn';
                    btn.innerHTML = `
                                        <span class="stock-main">
                                            ${s['證券代號']}<br>${s['證券名稱'] || ''}
                                        </span>
                                        <span class="remove-stock" title="移除自選" data-code="${s['證券代號']}">🗑️</span>
                                    `;
                    btn.onclick = function(e) {
                        if (e.target.classList.contains('remove-stock')) return;
                        showStockInfo(s['證券代號'], s['證券名稱']);
                    };
                    // 綁定刪除事件
                    btn.querySelector('.remove-stock').onclick = function(e) {
                        e.stopPropagation();
                        const code = this.getAttribute('data-code');
                        Swal.fire({
                            title: '確定要移除這檔股票嗎？',
                            text: `${s['證券代號']} ${s['證券名稱']}`,
                            icon: 'warning',
                            showCancelButton: true,
                            confirmButtonText: '移除',
                            cancelButtonText: '取消'
                        }).then((result) => {
                            if (result.isConfirmed) {
                                fetch('/remove_stock', {
                                    method: 'POST',
                                    headers: { 'Content-Type': 'application/json' },
                                    body: JSON.stringify({ '證券代號': code })
                                }).then(r => r.json()).then(rdata => {
                                    if (rdata.status === 'ok') {
                                        Swal.fire('成功', '已移除股票！', 'success').then(() => {
                                            load_user_stocks();
                                            // 清除container內容（如剛好顯示被刪股票）
                                            document.getElementById('container').innerHTML = `
                                                <h1>歡迎來到股票資訊網站</h1>
                                                <p>這裡是你的股票資訊平台，提供最新的股票市場動態。</p>
                                                <button>了解更多</button>
                                            `;
                                        });
                                    } else {
                                        Swal.fire('錯誤', rdata.msg || '移除失敗', 'error');
                                    }
                                });
                            }
                        });
                    };
                    container.appendChild(btn);
                });
            }
        });
}

// 在 container 顯示股票詳情並帶 loading
function showStockInfo(code, name) {
    const container = document.getElementById('container');
    container.innerHTML = `<div class="loading" style="font-size:22px; text-align:center; margin-top:32px;">載入中...</div>`;
    fetch(`/get_dividend_info?code=${code}`)
        .then(response => response.json())
        .then(stockData => {
            // 用 API 回傳的 key！注意大小寫
            let mainMonths = (stockData.Payment_cycle || []).map(m => `${m}月`).join('、') || '-';
            let html = `
                <div style="padding: 24px 8px 8px 8px;">
                  <h2>${name}（${code}）</h2>
                  <hr>
                  <p><b>常見配息月：</b>${mainMonths}</p>
                  <p><b>最新現金股利：</b> ${stockData.dividend ?? '-'} 元</p>
                  <p><b>成交價：</b> ${stockData.stock_transaction_price ?? '-'} 元</p>
                  <p><b>最新殖利率：</b> ${stockData.yield ?? '-'} %</p>
                </div>
            `;
            container.innerHTML = html;
        })
        .catch(e => {
            container.innerHTML = '<p style="color:red">查詢失敗，請稍後再試！</p>';
        });
}

// 點主畫面自動收回 sidebar (手機)
document.getElementById('container').addEventListener('click', function() {
    if (window.innerWidth <= 600) {
        document.getElementById('sidebar').classList.remove('open');
    }
});

// 視窗調整時恢復 sidebar
window.addEventListener('resize', function() {
    var sidebar = document.getElementById('sidebar');
    if (window.innerWidth > 600) {
        sidebar.classList.remove('open');
    }
});

// 頁面載入時自動呼叫
document.addEventListener('DOMContentLoaded', load_user_stocks);
