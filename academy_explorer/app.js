document.addEventListener('DOMContentLoaded', async () => {
    const academyList = document.getElementById('academyList');
    const searchInput = document.getElementById('searchInput');
    const regionSelect = document.getElementById('regionSelect');
    const filterBtns = document.querySelectorAll('.filter-btn');
    const academyModal = document.getElementById('academyModal');
    const closeModal = document.getElementById('closeModal');
    const modalBody = document.getElementById('modalBody');

    let currentCategory = 'all';
    let searchQuery = '';
    let currentRegion = regionSelect.value || '시흥 은행동';
    let academiesData = [];
    
    // Load favorites from localStorage
    let favorites = JSON.parse(localStorage.getItem('academyFavorites')) || [];

    // Save favorites
    function saveFavorites() {
        localStorage.setItem('academyFavorites', JSON.stringify(favorites));
    }

    // Fetch data from backend
    async function fetchAcademies() {
        try {
            // Build query params
            const params = new URLSearchParams();
            if (currentCategory !== 'all' && currentCategory !== 'favorites') params.append('category', currentCategory);
            if (searchQuery) params.append('query', searchQuery);
            params.append('region', currentRegion);

            const response = await fetch(`/api/academies?${params.toString()}`);
            const result = await response.json();
            academiesData = result.data;
            renderAcademies();
        } catch (error) {
            console.error('Error fetching data:', error);
            // In case of complete network failure, you could fallback here as well
            academiesData = typeof mockData !== 'undefined' ? mockData : [];
            renderAcademies();
        }
    }

    // Render Academy Cards
    function renderAcademies() {
        academyList.innerHTML = '';
        
        let filteredData = academiesData;
        
        // If viewing favorites, filter by favorites array
        if (currentCategory === 'favorites') {
            filteredData = filteredData.filter(academy => favorites.includes(academy.name + academy.address));
        }

        if (filteredData.length === 0) {
            academyList.innerHTML = `
                <div style="grid-column: 1/-1; text-align: center; padding: 3rem; color: var(--text-muted);">
                    <i class="ph ph-magnifying-glass" style="font-size: 3rem; margin-bottom: 1rem; color: #cbd5e1;"></i>
                    <p>검색 결과가 없습니다. 다른 검색어를 입력해보세요.</p>
                </div>
            `;
            return;
        }

        filteredData.forEach((academy, index) => {
            // Generate stars
            const fullStars = Math.floor(academy.rating);
            const halfStar = academy.rating % 1 >= 0.5 ? 1 : 0;
            const emptyStars = 5 - fullStars - halfStar;
            
            let starsHtml = '';
            for(let i=0; i<fullStars; i++) starsHtml += '<i class="ph-fill ph-star"></i>';
            if(halfStar) starsHtml += '<i class="ph-fill ph-star-half"></i>';
            for(let i=0; i<emptyStars; i++) starsHtml += '<i class="ph ph-star"></i>';

            const uniqueId = academy.name + academy.address;
            const isFav = favorites.includes(uniqueId);

            const card = document.createElement('div');
            card.className = 'academy-card';
            card.style.animationDelay = `${index * 0.1}s`;
            card.innerHTML = `
                <img src="${academy.image}" alt="${academy.name}" class="card-image">
                <div class="card-content">
                    <button class="fav-btn ${isFav ? 'active' : ''}" data-id="${uniqueId}">
                        <i class="${isFav ? 'ph-fill' : 'ph'} ph-heart"></i>
                    </button>
                    <span class="card-category">${academy.category}</span>
                    <h3 class="card-title">${academy.name}</h3>
                    <div class="card-rating">
                        ${starsHtml} ${academy.rating} <span>(${academy.reviewCount} 리뷰)</span>
                    </div>
                    <div class="card-info">
                        <div class="card-info-item">
                            <i class="ph ph-map-pin"></i>
                            <span>${academy.address}</span>
                        </div>
                        <div class="card-info-item">
                            <i class="ph ph-phone"></i>
                            <span>${academy.phone}</span>
                        </div>
                    </div>
                </div>
            `;
            
            // Handle favorite button click
            const favBtn = card.querySelector('.fav-btn');
            favBtn.addEventListener('click', (e) => {
                e.stopPropagation(); // Prevent opening modal
                const id = favBtn.getAttribute('data-id');
                if (favorites.includes(id)) {
                    favorites = favorites.filter(fav => fav !== id);
                    favBtn.classList.remove('active');
                    favBtn.innerHTML = '<i class="ph ph-heart"></i>';
                    // If we are currently in favorites tab, re-render
                    if (currentCategory === 'favorites') renderAcademies();
                } else {
                    favorites.push(id);
                    favBtn.classList.add('active');
                    favBtn.innerHTML = '<i class="ph-fill ph-heart"></i>';
                }
                saveFavorites();
            });
            
            card.addEventListener('click', () => openModal(academy));
            academyList.appendChild(card);
        });
    }

    // Open Modal
    function openModal(academy) {
        // Generate Programs HTML
        const programsHtml = academy.programs.map(prog => `
            <div class="program-item">
                <div class="program-item-main">
                    <h4>${prog.name}</h4>
                    <p><i class="ph ph-clock"></i> ${prog.duration} | ${prog.time}</p>
                </div>
                <div class="program-price">${prog.price}</div>
            </div>
        `).join('');

        // Generate Reviews HTML
        const reviewsHtml = academy.reviews.map(rev => `
            <div class="review-item">
                <div class="review-header">
                    <div class="review-author"><i class="ph-fill ph-user-circle"></i> ${rev.author}</div>
                    <div class="review-date">${rev.date}</div>
                </div>
                <div class="card-rating" style="margin-bottom: 0.5rem; font-size: 0.8rem;">
                    ${'<i class="ph-fill ph-star"></i>'.repeat(rev.rating)}
                </div>
                <div class="review-content">${rev.content}</div>
            </div>
        `).join('');

        modalBody.innerHTML = `
            <img src="${academy.image}" alt="${academy.name}" class="modal-header-img">
            <div class="modal-body-content">
                <span class="card-category" style="margin-bottom: 1rem;">${academy.category}</span>
                <h2 class="modal-title">${academy.name}</h2>
                <p class="modal-desc">${academy.description}</p>
                
                <div class="card-info" style="margin-bottom: 2rem;">
                    <div class="card-info-item" style="font-size: 1.1rem; color: var(--text-main);">
                        <i class="ph-fill ph-map-pin" style="color: var(--primary);"></i>
                        ${academy.address}
                    </div>
                    <div class="card-info-item" style="font-size: 1.1rem; color: var(--text-main);">
                        <i class="ph-fill ph-phone" style="color: var(--primary);"></i>
                        ${academy.phone}
                    </div>
                </div>

                <h3 class="section-title"><i class="ph-fill ph-book-open-text"></i> 추천 방학 프로그램</h3>
                <div class="program-list">
                    ${programsHtml}
                </div>

                <h3 class="section-title"><i class="ph-fill ph-chat-centered-text"></i> 리얼 후기 & 평가</h3>
                <div class="review-list">
                    ${reviewsHtml}
                </div>

                <div class="action-buttons">
                    <a href="tel:${academy.phone}" class="btn btn-primary"><i class="ph ph-phone-call"></i> 전화 상담하기</a>
                    <a href="${academy.mapUrl}" target="_blank" class="btn btn-secondary"><i class="ph ph-map-trifold"></i> 지도 보기</a>
                </div>
            </div>
        `;
        
        academyModal.classList.add('active');
        document.body.style.overflow = 'hidden'; // Prevent background scrolling
    }

    // Close Modal
    function closeModalFunc() {
        academyModal.classList.remove('active');
        document.body.style.overflow = '';
    }

    closeModal.addEventListener('click', closeModalFunc);
    academyModal.addEventListener('click', (e) => {
        if(e.target === academyModal) closeModalFunc();
    });

    // Filtering
    filterBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            filterBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentCategory = btn.getAttribute('data-category');
            
            if (currentCategory === 'favorites') {
                // If favorites, we just re-render local data
                renderAcademies();
            } else {
                fetchAcademies(); // Fetch from backend instead of local render
            }
        });
    });

    // Region Select
    regionSelect.addEventListener('change', (e) => {
        currentRegion = e.target.value;
        // Don't fetch if currently on favorites tab
        if (currentCategory !== 'favorites') {
            fetchAcademies();
        }
    });

    // Searching with debounce
    let searchTimeout;
    searchInput.addEventListener('input', (e) => {
        clearTimeout(searchTimeout);
        searchQuery = e.target.value;
        searchTimeout = setTimeout(() => {
            fetchAcademies();
        }, 300); // 300ms debounce
    });

    // Initial fetch
    fetchAcademies();
});
