document.addEventListener("DOMContentLoaded", () => {
    let activeCycleId = null;
    let currentState = null;
    let prevReverseMode = false;
    
    const tabCurrent = document.getElementById("tab-current");
    const tabAnalysis = document.getElementById("tab-analysis");
    const tabGuide = document.getElementById("tab-guide");
    
    const homePanel = document.getElementById("home-panel");
    const setupPanel = document.getElementById("setup-panel");
    const statusPanel = document.getElementById("status-panel");
    const analysisPanel = document.getElementById("analysis-panel");
    const guidePanel = document.getElementById("guide-panel");
    
    const mainTabs = document.getElementById("main-tabs");
    const headerSubtitle = document.getElementById("header-subtitle");
    const cycleCardsContainer = document.getElementById("cycle-cards-container");
    const logoBtn = document.getElementById("logo-btn");
    const btnShowSetup = document.getElementById("btn-show-setup");

    function hideAllPanels() {
        homePanel.classList.add("hidden");
        setupPanel.classList.add("hidden");
        statusPanel.classList.add("hidden");
        analysisPanel.classList.add("hidden");
        guidePanel.classList.add("hidden");
        document.getElementById("record-btn").classList.add("hidden");
    }

    function showToast(message, type = "info") {
        const container = document.getElementById("toast-container");
        const toast = document.createElement("div");
        const bgColor = type === "danger" ? "#fee2e2" : type === "success" ? "#dcfce7" : "#e0e7ff";
        const color = type === "danger" ? "#ef4444" : type === "success" ? "#22c55e" : "#6366f1";
        
        toast.style.background = bgColor;
        toast.style.color = color;
        toast.style.padding = "12px 20px";
        toast.style.borderRadius = "8px";
        toast.style.boxShadow = "0 4px 6px -1px rgba(0, 0, 0, 0.1)";
        toast.style.fontWeight = "600";
        toast.style.fontSize = "0.9rem";
        toast.style.animation = "slideIn 0.3s ease-out";
        toast.textContent = message;
        
        container.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = "0";
            toast.style.transition = "opacity 0.3s";
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    // Logo Click -> Home
    logoBtn.addEventListener("click", () => {
        activeCycleId = null;
        loadHome();
    });

    // Show Setup Click
    btnShowSetup.addEventListener("click", () => {
        activeCycleId = null;
        hideAllPanels();
        mainTabs.style.display = "none";
        headerSubtitle.style.display = "none";
        setupPanel.classList.remove("hidden");
    });

    tabCurrent.addEventListener("click", () => {
        hideAllPanels();
        tabCurrent.classList.add("active");
        tabAnalysis.classList.remove("active");
        tabGuide.classList.remove("active");
        if(currentState && currentState.active) {
            statusPanel.classList.remove("hidden");
            document.getElementById("record-btn").classList.remove("hidden");
        } else {
            setupPanel.classList.remove("hidden");
        }
    });

    tabAnalysis.addEventListener("click", () => {
        hideAllPanels();
        tabAnalysis.classList.add("active");
        tabCurrent.classList.remove("active");
        tabGuide.classList.remove("active");
        if(currentState && currentState.active) {
            analysisPanel.classList.remove("hidden");
            generateCalculatorTable();
        }
    });

    tabGuide.addEventListener("click", () => {
        hideAllPanels();
        tabGuide.classList.add("active");
        tabCurrent.classList.remove("active");
        tabAnalysis.classList.remove("active");
        guidePanel.classList.remove("hidden");
    });

    // Setup Form Interactions
    const setupForm = document.getElementById("setup-form");
    const symbolBtns = document.querySelectorAll("#symbol-group .radio-btn");
    const paramSymbol = document.getElementById("param-symbol");
    symbolBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            symbolBtns.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            const val = btn.getAttribute("data-val");
            paramSymbol.value = val;
            if (val === "CUSTOM") {
                const customSym = prompt("종목 심볼을 입력하세요 (예: TQQQ):", "TQQQ");
                if (customSym) paramSymbol.value = customSym.toUpperCase();
            }
        });
    });

    const splitBtns = document.querySelectorAll("#split-group .radio-btn");
    const paramSplit = document.getElementById("param-split");
    splitBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            splitBtns.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            paramSplit.value = btn.getAttribute("data-val");
        });
    });

    const modeBtns = document.querySelectorAll(".mode-btn");
    const paramMode = document.getElementById("param-mode");
    const autoSetupGroup = document.getElementById("auto-setup-group");
    modeBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            modeBtns.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            const mode = btn.getAttribute("data-val");
            paramMode.value = mode;
            if (mode === "auto") {
                autoSetupGroup.classList.remove("hidden");
            } else {
                autoSetupGroup.classList.add("hidden");
            }
        });
    });

    setupForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const newSymbol = document.getElementById("param-symbol").value.toUpperCase();
        const nameInput = document.getElementById("param-name");
        const payload = {
            name: nameInput ? nameInput.value : "",
            symbol: newSymbol,
            total_budget: parseFloat(document.getElementById("param-budget").value),
            split_count: parseInt(document.getElementById("param-split").value),
            commission_rate: 0, 
            initial_loc_pct: parseFloat(document.getElementById("param-initial-loc-pct").value),
            sudden_drop_pct: parseFloat(document.getElementById("param-sudden-drop").value),
            is_auto_mode: document.getElementById("param-mode").value === "auto"
        };

        const res = await fetch("/api/cycle", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        if (res.ok) {
            const data = await res.json();
            activeCycleId = data.cycle_id;
            fetchState();
        } else {
            const err = await res.json();
            alert("오류: " + (err.detail || "사이클 생성에 실패했습니다."));
        }
    });

    async function loadHome() {
        hideAllPanels();
        mainTabs.style.display = "none";
        headerSubtitle.style.display = "none";
        
        try {
            const res = await fetch("/api/cycles");
            const data = await res.json();
            const cycles = data.cycles;
            
            if (cycles.length === 0) {
                setupPanel.classList.remove("hidden");
                return;
            }
            
            homePanel.classList.remove("hidden");
            cycleCardsContainer.innerHTML = "<p style='text-align:center; color:var(--text-muted);'>데이터를 불러오는 중...</p>";
            
            let cardsHtml = "";
            for (let cInfo of cycles) {
                const cRes = await fetch(`/api/cycle?cycle_id=${cInfo.cycle_id}`);
                const cState = await cRes.json();
                if (cState.active) {
                    let statusColor = cState.reverse_mode ? "var(--danger)" : "var(--primary)";
                    let statusBg = cState.reverse_mode ? "#FEE2E2" : "#E0E7FF";
                    let statusText = cState.reverse_mode ? "리버스 모드" : (cState.T === 0 ? "처음매수" : `T=${cState.T.toFixed(cState.T % 1 === 0 ? 0 : 3)}`);
                    let displayName = cState.name ? `[${cState.name}] ${cState.symbol}` : cState.symbol;
                    
                    cardsHtml += `
                        <div class="cycle-card" data-cycle-id="${cState.cycle_id}">
                            <div>
                                <div class="cycle-card-title">${displayName}</div>
                                <div class="cycle-card-subtitle">${cState.split_count}분할 · 예산 $${cState.total_budget.toLocaleString()}</div>
                            </div>
                            <div class="cycle-card-status" style="background: ${statusBg}; color: ${statusColor};">
                                ${statusText}
                            </div>
                        </div>
                    `;
                }
            }
            cycleCardsContainer.innerHTML = cardsHtml;
            
            document.querySelectorAll(".cycle-card").forEach(card => {
                card.addEventListener("click", () => {
                    activeCycleId = card.getAttribute("data-cycle-id");
                    fetchState();
                });
            });
            
        } catch (err) {
            console.error("Home loading failed", err);
        }
    }

    // Parameters Updates
    const locPctBtns = document.querySelectorAll(".loc-pct-btn");
    locPctBtns.forEach(btn => {
        btn.addEventListener("click", async () => {
            const val = parseFloat(btn.getAttribute("data-val"));
            const res = await fetch(`/api/cycle/loc_pct?cycle_id=${activeCycleId}`, {
                method: "PATCH",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({initial_loc_pct: val})
            });
            if (res.ok) fetchState();
        });
    });

    const sdPctBtns = document.querySelectorAll(".sd-pct-btn");
    sdPctBtns.forEach(btn => {
        btn.addEventListener("click", async () => {
            const val = parseFloat(btn.getAttribute("data-val"));
            const res = await fetch(`/api/cycle/sudden_drop_pct?cycle_id=${activeCycleId}`, {
                method: "PATCH",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({sudden_drop_pct: val})
            });
            if (res.ok) fetchState();
        });
    });

    // Record Action Modal Logic
    const recordBtn = document.getElementById("record-btn");
    const recordModal = document.getElementById("record-modal");
    const closeModal = document.getElementById("close-modal");
    const actionBtns = document.querySelectorAll(".action-btn");
    const fillDetails = document.getElementById("fill-details");
    const confirmActionBtn = document.getElementById("confirm-action-btn");
    let selectedAction = null;

    recordBtn.addEventListener("click", () => {
        recordModal.classList.remove("hidden");
        fillDetails.classList.add("hidden");
        
        if (currentState && currentState.reverse_mode) {
            document.getElementById("normal-actions").classList.add("hidden");
            document.getElementById("reverse-actions").classList.remove("hidden");
        } else {
            document.getElementById("normal-actions").classList.remove("hidden");
            document.getElementById("reverse-actions").classList.add("hidden");
        }
    });

    closeModal.addEventListener("click", () => {
        recordModal.classList.add("hidden");
        selectedAction = null;
    });

    actionBtns.forEach(btn => {
        btn.addEventListener("click", (e) => {
            selectedAction = btn.getAttribute("data-action");
            fillDetails.classList.remove("hidden");
            
            if (currentState) {
                if (selectedAction === "take_profit") {
                    document.getElementById("action-qty").value = currentState.quantity;
                    const tpRatio = currentState.symbol === "SOXL" ? 1.20 : 1.15;
                    document.getElementById("action-price").value = (currentState.avg_price * tpRatio).toFixed(2);
                } 
                else if (selectedAction === "quarter_sell") {
                    document.getElementById("action-qty").value = Math.floor(currentState.quantity / 4);
                    document.getElementById("action-price").value = currentState.current_star_price > 0 ? currentState.current_star_price.toFixed(2) : "";
                }
                else {
                    document.getElementById("action-qty").value = "";
                    document.getElementById("action-price").value = currentState.current_star_price > 0 ? currentState.current_star_price.toFixed(2) : "";
                }
            }
        });
    });

    confirmActionBtn.addEventListener("click", async () => {
        if (!selectedAction) return;
        
        const price = parseFloat(document.getElementById("action-price").value);
        const qty = parseFloat(document.getElementById("action-qty").value);
        const tradeDateVal = document.getElementById("manual-record-date").value;
        
        if (!price || isNaN(qty)) {
            alert("가격을 정확히 입력하세요.");
            return;
        }

        const payload = {
            action: selectedAction,
            price: price,
            quantity: qty,
            trade_date: tradeDateVal || null
        };

        const res = await fetch(`/api/action?cycle_id=${activeCycleId}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        
        if (res.ok) {
            recordModal.classList.add("hidden");
            fillDetails.classList.add("hidden");
            document.getElementById("action-price").value = "";
            document.getElementById("action-qty").value = "";
            document.getElementById("orders-list").innerHTML = "";
            fetchState();
        }
    });

    // Brokers and Automations
    const btnAutoSync = document.getElementById("btn-auto-sync");
    const autoSyncLoading = document.getElementById("auto-sync-loading");
    if(btnAutoSync) {
        btnAutoSync.addEventListener("click", async () => {
            btnAutoSync.disabled = true;
            autoSyncLoading.classList.remove("hidden");
            
            try {
                const res = await fetch(`/api/action/auto_sync?cycle_id=${activeCycleId}`, {
                    method: "POST"
                });
                const data = await res.json();
                
                if (res.ok) {
                    alert(`자동 동기화 완료!\n${data.message}`);
                    recordModal.classList.add("hidden");
                    fillDetails.classList.add("hidden");
                    fetchState();
                } else {
                    alert(`자동 동기화 실패: ${data.detail}`);
                }
            } catch (err) {
                alert("서버 연결에 실패했습니다.");
            } finally {
                btnAutoSync.disabled = false;
                autoSyncLoading.classList.add("hidden");
            }
        });
    }

    const btnSubmitKis = document.getElementById("btn-submit-kis");
    const kisSubmitLoading = document.getElementById("kis-submit-loading");
    if (btnSubmitKis) {
        btnSubmitKis.addEventListener("click", async () => {
            btnSubmitKis.disabled = true;
            kisSubmitLoading.classList.remove("hidden");
            
            try {
                const res = await fetch(`/api/action/submit_to_broker?cycle_id=${activeCycleId}`, {
                    method: "POST"
                });
                const data = await res.json();
                
                if (res.ok) {
                    let successCount = data.results.filter(r => r.status === "SUCCESS").length;
                    if (successCount === data.results.length && successCount > 0) {
                        showToast(`✅ ${data.message}`, "success");
                    } else if (successCount > 0) {
                        showToast(`⚠️ 일부 주문 실패: ${data.message}`);
                    } else {
                        showToast(`❌ 전송 실패: ${data.message}`, "danger");
                    }
                } else {
                    showToast(`❌ 에러: ${data.detail}`, "danger");
                }
            } catch (err) {
                showToast("❌ 서버 접속 오류", "danger");
            } finally {
                btnSubmitKis.disabled = false;
                kisSubmitLoading.classList.add("hidden");
            }
        });
    }

    const btnDeleteCycle = document.getElementById("btn-delete-cycle");
    if (btnDeleteCycle) {
        btnDeleteCycle.addEventListener("click", async () => {
            const confirmed = confirm("⚠️ 정말로 이 사이클을 강제 종료하고 삭제하시겠습니까?\n\n모든 진행 기록이 즉시 삭제되며 복구할 수 없습니다.");
            if (confirmed) {
                try {
                    const res = await fetch(`/api/cycle/reset?cycle_id=${activeCycleId}`, {
                        method: "DELETE"
                    });
                    if (res.ok) {
                        alert("사이클이 성공적으로 삭제되었습니다.");
                        activeCycleId = null;
                        loadHome();
                    } else {
                        alert("삭제에 실패했습니다.");
                    }
                } catch (err) {
                    alert("서버 연결에 실패했습니다.");
                }
            }
        });
    }

    async function fetchOrdersToday() {
        try {
            document.getElementById("today-ref-price").textContent = "로딩중...";
            const res = await fetch(`/api/orders/today?cycle_id=${activeCycleId}`);
            if (res.ok) {
                const data = await res.json();
                document.getElementById("today-ref-price").textContent = `기준가: $${data.ref_price.toFixed(2)}`;
                renderOrders(data.orders);
                
                if (currentState && currentState.T === 0 && !currentState.reverse_mode) {
                    document.getElementById("t0-new-cycle-header").classList.remove("hidden");
                    document.getElementById("t0-ref-price").textContent = `$${data.ref_price.toFixed(2)}`;
                    
                    const currentPct = currentState.initial_loc_pct || 0.15;
                    document.getElementById("t0-loc-pct-text").textContent = `+${(currentPct * 100).toFixed(0)}%`;
                    const bigPrice = data.ref_price * (1 + currentPct);
                    document.getElementById("t0-loc-price").textContent = `$${bigPrice.toFixed(2)}`;
                    
                    document.querySelectorAll(".loc-pct-btn").forEach(b => {
                        const val = parseFloat(b.getAttribute("data-val"));
                        if (Math.abs(val - currentPct) < 0.001) {
                            b.classList.add("active");
                            b.style.borderColor = "#ea580c";
                            b.style.color = "#ea580c";
                        } else {
                            b.classList.remove("active");
                            b.style.borderColor = "var(--border-color)";
                            b.style.color = "var(--text-main)";
                        }
                    });
                } else {
                    document.getElementById("t0-new-cycle-header").classList.add("hidden");
                }
            } else {
                document.getElementById("today-ref-price").textContent = "주문 불러오기 실패";
                document.getElementById("t0-new-cycle-header").classList.add("hidden");
            }
        } catch (err) {
            document.getElementById("today-ref-price").textContent = "에러 발생";
        }
    }

    function renderOrders(orders) {
        const container = document.getElementById("orders-list");
        container.innerHTML = "";

        if (!orders || orders.length === 0) {
            container.innerHTML = "<p style='color: var(--text-muted); text-align: center; padding: 20px;'>오늘 생성할 주문이 없습니다.</p>";
            return;
        }

        orders.forEach(o => {
            const el = document.createElement("div");
            el.className = `order-item ${o.tag.includes("매도") || o.tag.includes("익절") ? "sell" : "buy"}`;
            el.innerHTML = `
                <div>
                    <div class="order-tag">${o.tag} (${o.kind})</div>
                    <div class="order-price">$${o.price.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</div>
                </div>
                <div class="order-qty">${o.quantity} 주</div>
            `;
            container.appendChild(el);
        });
    }

    function generateCalculatorTable() {
        if (!currentState) return;
        const tbody = document.getElementById("calc-table-body");
        tbody.innerHTML = "";

        const splits = currentState.split_count;
        const symbol = currentState.symbol;
        const avgPrice = currentState.avg_price;

        for (let t = 0; t <= splits; t++) {
            let starPct = 0;
            if (symbol === "SOXL") {
                starPct = splits === 40 ? (0.20 - (0.01 * t)) : (0.20 - (0.02 * t));
            } else {
                starPct = splits === 40 ? (0.15 - (0.0075 * t)) : (0.15 - (0.015 * t));
            }

            const starPrice = avgPrice > 0 ? avgPrice * (1 + starPct) : 0;
            const isSecondHalf = t >= splits / 2;

            const tr = document.createElement("tr");
            if (isSecondHalf) {
                tr.style.backgroundColor = "#F1F5F9";
            }
            tr.style.borderBottom = "1px solid var(--border-color)";

            tr.innerHTML = `
                <td style="padding: 10px;">${t}</td>
                <td style="padding: 10px; color: ${starPct > 0 ? 'var(--success)' : (starPct < 0 ? 'var(--danger)' : 'var(--text-main)')}">
                    ${starPct > 0 ? '+' : ''}${(starPct * 100).toFixed(2)}%
                </td>
                <td style="padding: 10px;">${avgPrice > 0 ? '$' + starPrice.toFixed(2) : '-'}</td>
            `;
            tbody.appendChild(tr);
        }
    }

    async function fetchState() {
        try {
            if (!activeCycleId) {
                loadHome();
                return;
            }

            const res = await fetch(`/api/cycle?cycle_id=${activeCycleId}`);
            const state = await res.json();
            currentState = state;

            if (currentState.active) {
                hideAllPanels();
                mainTabs.style.display = "flex";
                headerSubtitle.style.display = "block";
                
                // Show current panel by default if no tab is active or tabCurrent is active
                tabCurrent.classList.add("active");
                tabAnalysis.classList.remove("active");
                tabGuide.classList.remove("active");
                statusPanel.classList.remove("hidden");
                document.getElementById("record-btn").classList.remove("hidden");

                let displayName = currentState.name ? `[${currentState.name}] ${currentState.symbol}` : currentState.symbol;
                document.getElementById("head-symbol").textContent = displayName;
                document.getElementById("head-split").textContent = `${currentState.split_count}분할`;
                document.getElementById("head-budget").textContent = `$${currentState.total_budget.toLocaleString()}`;

                document.getElementById("val-t").textContent = state.T.toFixed(state.T % 1 === 0 ? 0 : 3);
                document.getElementById("val-split").textContent = state.split_count;
                
                const pct = Math.min(100, (state.T / state.split_count) * 100);
                document.getElementById("t-progress").style.width = `${pct}%`;
                
                const badge = document.getElementById("badge-status");
                if (state.reverse_mode) {
                    badge.textContent = "리버스 모드";
                    badge.style.background = "#FEE2E2";
                    badge.style.color = "#EF4444";
                    document.getElementById("t-progress").style.background = "#EF4444";
                } else if (state.T === 0) {
                    badge.textContent = "처음매수";
                    badge.style.background = "#E0E7FF";
                    badge.style.color = "#6366F1";
                    document.getElementById("t-progress").style.background = "#6366F1";
                } else if (state.T >= state.split_count / 2) {
                    badge.textContent = "후반전";
                } else {
                    badge.textContent = "전반전";
                }

                document.getElementById("val-qty").textContent = state.quantity;
                document.getElementById("val-avg-price").textContent = `$${state.avg_price.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
                document.getElementById("val-cash").textContent = `$${state.cash_remaining.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
                
                document.getElementById("val-star-pct").textContent = `${state.current_star_pct > 0 ? '+' : ''}${(state.current_star_pct * 100).toFixed(2)}%`;
                document.getElementById("val-star-price").textContent = `$${state.current_star_price.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
                document.getElementById("val-budget").textContent = `$${state.current_one_lot_budget.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;

                const tpText = document.getElementById("take-profit-text");
                if(tpText) {
                    tpText.textContent = `지정가 익절 (+${state.symbol === "SOXL" ? "20" : "15"}%)`;
                }

                if (state.reverse_mode && !prevReverseMode) {
                    showToast("⚠️ 잔고가 부족하여 리버스 모드에 진입했습니다.", "danger");
                } else if (!state.reverse_mode && prevReverseMode) {
                    showToast("✅ 평단 회복! 일반 모드로 복귀했습니다.", "success");
                }
                prevReverseMode = state.reverse_mode;

                const manualSdContainer = document.getElementById("manual-sudden-drop-container");
                if (!state.is_auto_mode) {
                    manualSdContainer.classList.remove("hidden");
                    const currentDropPct = state.sudden_drop_pct || 0;
                    document.querySelectorAll(".sd-pct-btn").forEach(b => {
                        const val = parseFloat(b.getAttribute("data-val"));
                        if (Math.abs(val - currentDropPct) < 0.001) {
                            b.classList.add("active");
                            b.style.borderColor = "#ef4444";
                            b.style.color = "#ef4444";
                        } else {
                            b.classList.remove("active");
                            b.style.borderColor = "var(--border-color)";
                            b.style.color = "var(--text-main)";
                        }
                    });
                } else {
                    manualSdContainer.classList.add("hidden");
                }

                const dateInput = document.getElementById("manual-record-date");
                if (dateInput && !dateInput.value) {
                    const todayStr = new Date().toISOString().split('T')[0];
                    dateInput.value = todayStr;
                }
                renderHistory(state.fills);
                try {
                    const histRes = await fetch(`/api/history-prices/${state.symbol}`);
                    if (histRes.ok) {
                        const history = await histRes.json();
                        renderDateCards(history);
                    }
                } catch (e) {
                    console.error("Failed to fetch history prices:", e);
                }
                fetchOrdersToday();

            } else {
                activeCycleId = null;
                loadHome();
            }
        } catch (err) {
            console.error("Failed to fetch state:", err);
        }
    }

    // Initialize
    loadHome();

    // Manual Sync Logic
    const syncModal = document.getElementById("sync-modal");
    const btnOpenSync = document.getElementById("btn-open-sync");
    const btnCancelSync = document.getElementById("btn-cancel-sync");
    const btnSubmitSync = document.getElementById("btn-submit-sync");
    const closeSyncModalBtn = document.getElementById("close-sync-modal");

    if (btnOpenSync && syncModal) {
        btnOpenSync.addEventListener("click", () => {
            document.getElementById("sync-quantity").value = "";
            document.getElementById("sync-avg-price").value = "";
            syncModal.classList.remove("hidden");
        });

        const closeSync = () => syncModal.classList.add("hidden");
        btnCancelSync.addEventListener("click", closeSync);
        closeSyncModalBtn.addEventListener("click", closeSync);

        btnSubmitSync.addEventListener("click", async () => {
            const qty = parseFloat(document.getElementById("sync-quantity").value);
            const price = parseFloat(document.getElementById("sync-avg-price").value);
            
            if (isNaN(qty) || isNaN(price)) {
                alert("수량과 평단가를 정확히 입력해주세요.");
                return;
            }

            try {
                const res = await fetch(`/api/cycle/sync?cycle_id=${activeCycleId}`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ quantity: qty, avg_price: price })
                });
                
                if (res.ok) {
                    showToast("✅ 보유 내역이 성공적으로 동기화되었습니다.", "success");
                    closeSync();
                    fetchState();
                } else {
                    const err = await res.json();
                    alert("오류: " + (err.detail || "동기화 실패"));
                }
            } catch (e) {
                console.error(e);
                alert("네트워크 오류가 발생했습니다.");
            }
        });
    }

    // Force Delete Logic
    const btnForceDelete = document.getElementById("btn-force-delete");
    if (btnForceDelete) {
        btnForceDelete.addEventListener("click", async () => {
            if (confirm("정말 이 사이클을 삭제하시겠습니까? 복구할 수 없습니다!")) {
                try {
                    const res = await fetch(`/api/cycle/reset?cycle_id=${activeCycleId}`, {
                        method: "DELETE"
                    });
                    if (res.ok) {
                        alert("사이클이 삭제되었습니다.");
                        loadHome();
                    }
                } catch (e) {
                    console.error(e);
                }
            }
        });
    }

    function renderHistory(fills) {
        const countEl = document.getElementById("history-count");
        const listEl = document.getElementById("history-list");
        
        if (!countEl || !listEl) return;
        
        countEl.textContent = fills ? fills.length : 0;
        listEl.innerHTML = "";
        
        if (!fills || fills.length === 0) {
            listEl.innerHTML = "<p style='color: var(--text-muted); text-align: center; padding: 15px; font-size: 0.9rem;'>기록된 매매 히스토리가 없습니다.</p>";
            return;
        }
        
        const reversedFills = [...fills].reverse();
        const groups = {};
        reversedFills.forEach(f => {
            const d = f.trade_date;
            if (!groups[d]) groups[d] = [];
            groups[d].push(f);
        });
        
        let html = "";
        for (let dateStr in groups) {
            html += `
                <div class="history-group" style="margin-bottom: 12px;">
                    <div style="font-weight: 700; font-size: 0.9rem; color: var(--text-muted); margin-bottom: 6px;">${dateStr}</div>
                    <div style="display: flex; flex-direction: column; gap: 6px;">
            `;
            for (let f of groups[dateStr]) {
                let actionText = "";
                if (f.action === "full_buy") actionText = "1회 매수";
                else if (f.action === "half_buy") actionText = "절반 매수";
                else if (f.action === "first_buy") actionText = "첫 진입";
                else if (f.action === "reverse_buy") actionText = "리버스 매수";
                else if (f.action === "reverse_sell") actionText = "무한 매도";
                else if (f.action === "quarter_sell") actionText = "LOC 매도";
                else if (f.action === "take_profit") actionText = "전량 익절";
                else actionText = f.side === "BUY" ? "매수" : "매도";

                let sideColor = f.side === "BUY" ? "#ef4444" : "#2563eb";
                let sideBg = f.side === "BUY" ? "#fef2f2" : "#eff6ff";
                let totalVal = f.price * f.quantity;
                
                html += `
                    <div style="display: flex; justify-content: space-between; align-items: center; background: var(--bg-body); border: 1px solid var(--border-color); padding: 8px 12px; border-radius: 8px; font-size: 0.9rem;">
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <span style="background: ${sideBg}; color: ${sideColor}; font-size: 0.75rem; font-weight: 700; padding: 2px 6px; border-radius: 4px;">${actionText}</span>
                            <span style="font-weight: 600; color: var(--text-main);">$${f.price.toFixed(2)} × ${f.quantity}주</span>
                        </div>
                        <div style="font-weight: 700; color: var(--text-muted);">$${totalVal.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</div>
                    </div>
                `;
            }
            html += `
                    </div>
                </div>
            `;
        }
        listEl.innerHTML = html;
    }

    const btnDeleteLastHistory = document.getElementById("btn-delete-last-history");
    if (btnDeleteLastHistory) {
        btnDeleteLastHistory.addEventListener("click", async () => {
            if (!confirm("⚠️ 가장 최근에 기록된 매매 날짜의 기록을 정말 삭제하시겠습니까?\n\n삭제 시 이전 상태로 재계산(Replay)됩니다.")) return;
            
            try {
                const res = await fetch(`/api/action/last?cycle_id=${activeCycleId}`, {
                    method: "DELETE"
                });
                if (res.ok) {
                    showToast("✅ 최근 거래가 성공적으로 삭제되었습니다.", "success");
                    fetchState();
                } else {
                    const err = await res.json();
                    alert("오류: " + (err.detail || "삭제 실패"));
                }
            } catch (e) {
                console.error(e);
                alert("네트워크 오류가 발생했습니다.");
            }
        });
    }

    function renderDateCards(history) {
        const scrollEl = document.getElementById("date-cards-scroll");
        if (!scrollEl) return;
        scrollEl.innerHTML = "";
        
        if (!history || history.length === 0) {
            scrollEl.innerHTML = "<p style='color: var(--text-muted); font-size: 0.85rem; padding: 10px;'>최근 종가 정보를 불러올 수 없습니다.</p>";
            return;
        }
        
        history.forEach((h, i) => {
            let arrow = "";
            let arrowColor = "var(--text-muted)";
            if (i > 0) {
                const prevClose = history[i-1].close;
                if (h.close > prevClose) {
                    arrow = "▲";
                    arrowColor = "#ef4444"; // red up
                } else if (h.close < prevClose) {
                    arrow = "▼";
                    arrowColor = "#2563eb"; // blue down
                }
            }
            
            const card = document.createElement("div");
            card.className = "date-card";
            card.style.flex = "0 0 95px";
            card.style.background = "var(--bg-body)";
            card.style.border = "1px solid var(--border-color)";
            card.style.borderRadius = "12px";
            card.style.padding = "10px 8px";
            card.style.textAlign = "center";
            card.style.cursor = "pointer";
            card.style.transition = "all 0.2s";
            
            card.innerHTML = `
                <div style="font-size: 0.8rem; font-weight: 700; color: var(--text-main); margin-bottom: 2px;">
                    ${h.date} <span style="color: ${arrowColor}; font-size: 0.75rem;">${arrow}</span>
                </div>
                <div style="font-size: 0.65rem; color: var(--text-muted); margin-bottom: 4px;">종가</div>
                <div style="font-size: 0.9rem; font-weight: 800; color: var(--text-main);">$${h.close.toFixed(2)}</div>
            `;
            
            card.addEventListener("click", () => {
                document.querySelectorAll(".date-card").forEach(c => {
                    c.style.borderColor = "var(--border-color)";
                    c.style.background = "var(--bg-body)";
                    c.style.boxShadow = "none";
                });
                card.style.borderColor = "#3b82f6"; // blue border
                card.style.background = "rgba(59, 130, 246, 0.05)"; // light blue bg
                card.style.boxShadow = "0 4px 12px rgba(59, 130, 246, 0.1)";
                
                selectDateCard(h.full_date, h.close);
            });
            
            scrollEl.appendChild(card);
        });
    }

    function selectDateCard(dateStr, closePrice) {
        document.getElementById("selected-plan-date").textContent = dateStr;
        document.getElementById("selected-plan-close").textContent = `$${closePrice.toFixed(2)}`;
        document.getElementById("manual-record-date").value = dateStr;
        
        const container = document.getElementById("plan-buttons-container");
        if (!container) return;
        container.innerHTML = "";
        
        const box = document.getElementById("trade-plan-box");
        if (box) box.classList.remove("hidden");
        
        const isTqqq = currentState.symbol === "TQQQ";
        const flatQty = isTqqq ? 3 : 1;
        const starQty = 1;
        
        let buttons = [];
        
        if (currentState.T === 0) {
            buttons.push({
                label: `[첫 진입 매수 적용] $${closePrice.toFixed(2)} × 1주 (T+1.0)`,
                action: "first_buy",
                price: closePrice,
                qty: 1,
                color: "btn-primary"
            });
        } else if (currentState.reverse_mode) {
            const revBuyQty = Math.max(1, Math.floor((currentState.current_one_lot_budget / 4) / closePrice));
            const revSellQty = currentState.quantity > 0 ? (currentState.reverse_sell_qty_unit || 1) : 1;
            
            buttons.push({
                label: `[리버스 매수 적용] $${closePrice.toFixed(2)} × ${revBuyQty}주`,
                action: "reverse_buy",
                price: closePrice,
                qty: revBuyQty,
                color: "btn-primary"
            });
            
            if (currentState.quantity > 0) {
                buttons.push({
                    label: `[무한 매도 적용] $${closePrice.toFixed(2)} × ${revSellQty}주`,
                    action: "reverse_sell",
                    price: closePrice,
                    qty: revSellQty,
                    color: "btn-outline"
                });
            }
        } else {
            const fullQty = flatQty + starQty;
            
            buttons.push({
                label: `[1회 매수 적용] $${closePrice.toFixed(2)} × ${fullQty}주 (T+1.0)`,
                action: "full_buy",
                price: closePrice,
                qty: fullQty,
                color: "btn-primary"
            });
            
            buttons.push({
                label: `[절반 매수 적용] $${closePrice.toFixed(2)} × ${flatQty}주 (T+0.5)`,
                action: "half_buy",
                price: closePrice,
                qty: flatQty,
                color: "btn-primary",
                style: "background-color: #f97316; border-color: #f97316;"
            });
            
            if (currentState.T >= currentState.split_count / 2 && currentState.quantity > 0) {
                const locSellQty = isTqqq ? 3 : 1;
                const quarterSellQty = Math.max(1, Math.floor(currentState.quantity * 0.25));
                
                buttons.push({
                    label: `[무한 매도 적용] $${closePrice.toFixed(2)} × ${locSellQty}주 (후반전 LOC 매도)`,
                    action: "reverse_sell",
                    price: closePrice,
                    qty: locSellQty,
                    color: "btn-outline"
                });
                
                buttons.push({
                    label: `[LOC 매도 적용] $${closePrice.toFixed(2)} × ${quarterSellQty}주 (별지점 LOC 매도)`,
                    action: "quarter_sell",
                    price: closePrice,
                    qty: quarterSellQty,
                    color: "btn-outline"
                });
            }
        }
        
        if (currentState.quantity > 0) {
            const tpPct = currentState.symbol === "SOXL" ? 1.20 : 1.15;
            const tpPrice = currentState.avg_price * tpPct;
            buttons.push({
                label: `[전량 익절 적용] $${tpPrice.toFixed(2)} × ${currentState.quantity}주 (T=0)`,
                action: "take_profit",
                price: tpPrice,
                qty: currentState.quantity,
                color: "btn-outline",
                style: "border-color: #10b981; color: #10b981;"
            });
        }
        
        buttons.forEach(b => {
            const btn = document.createElement("button");
            btn.className = `btn ${b.color}`;
            btn.style.width = "100%";
            btn.style.padding = "10px";
            btn.style.fontSize = "0.9rem";
            btn.style.fontWeight = "600";
            btn.style.justifyContent = "center";
            if (b.style) {
                btn.setAttribute("style", btn.getAttribute("style") + "; " + b.style);
            }
            btn.textContent = b.label;
            
            btn.addEventListener("click", async () => {
                if (!confirm(`'${b.label}' 매매를 기록하시겠습니까?`)) return;
                
                try {
                    const res = await fetch(`/api/action?cycle_id=${activeCycleId}`, {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            action: b.action,
                            price: b.price,
                            quantity: b.qty,
                            trade_date: dateStr
                        })
                    });
                    if (res.ok) {
                        showToast("✅ 성공적으로 기록되었습니다.", "success");
                        box.classList.add("hidden");
                        fetchState();
                    } else {
                        const err = await res.json();
                        alert("오류: " + (err.detail || "기록 실패"));
                    }
                } catch (e) {
                    console.error(e);
                    alert("네트워크 오류가 발생했습니다.");
                }
            });
            
            container.appendChild(btn);
        });
    }
});
