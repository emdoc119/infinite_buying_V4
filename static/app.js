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
        
        if (!price || isNaN(qty)) {
            alert("가격을 정확히 입력하세요.");
            return;
        }

        const payload = {
            action: selectedAction,
            price: price,
            quantity: qty
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
});
