document.addEventListener('DOMContentLoaded', () => {
    const bindingArea = document.getElementById('binding-area');
    const cardsContainer = document.getElementById('cards-container');
    const monthFiltersContainer = document.getElementById('month-filters');
    const carouselTrack = document.getElementById('carousel-track');

    const thaiMonthsFull = ['มกราคม', 'กุมภาพันธ์', 'มีนาคม', 'เมษายน', 'พฤษภาคม', 'มิถุนายน', 'กรกฎาคม', 'สิงหาคม', 'กันยายน', 'ตุลาคม', 'พฤศจิกายน', 'ธันวาคม'];
    const thaiMonthsAbbr = ['ม.ค.', 'ก.พ.', 'มี.ค.', 'เม.ย.', 'พ.ค.', 'มิ.ย.', 'ก.ค.', 'ส.ค.', 'ก.ย.', 'ต.ค.', 'พ.ย.', 'ธ.ค.'];

    // Carousel state
    let carouselImages = [];
    let carouselIndex = 0;

    async function loadCarousel() {
        try {
            const res = await fetch('/api/carousel');
            carouselImages = await res.json();
            renderCarousel();
            startCarousel();
        } catch(e) { console.error(e); }
    }

    function renderCarousel() {
        if (!carouselTrack) return;
        const container = document.getElementById('carousel-container');
        if (!container) return;
        const width = 320;
        
        carouselTrack.innerHTML = '';
        carouselImages.forEach(src => {
            const img = document.createElement('img');
            img.src = src;
            img.style.width = width + 'px';
            carouselTrack.appendChild(img);
        });
        if (carouselImages.length > 1) {
            const firstClone = document.createElement('img');
            firstClone.src = carouselImages[0];
            firstClone.style.width = width + 'px';
            carouselTrack.appendChild(firstClone);
        }
    }

    function startCarousel() {
        if (carouselImages.length <= 1) return;
        setInterval(() => {
            const container = document.getElementById('carousel-container');
            if (!container) return;
            const width = 320;
            
            carouselIndex++;
            carouselTrack.style.transform = `translateX(-${carouselIndex * width}px)`;
            
            if (carouselIndex >= carouselImages.length) {
                setTimeout(() => {
                    carouselTrack.style.transition = 'none';
                    carouselIndex = 0;
                    carouselTrack.style.transform = `translateX(0)`;
                    setTimeout(() => {
                        carouselTrack.style.transition = 'transform 0.8s cubic-bezier(0.4, 0, 0.2, 1)';
                    }, 50);
                }, 800);
            }
        }, 4000);
    }

    // Handle resize
    window.addEventListener('resize', () => {
        renderCarousel();
        carouselIndex = 0;
        carouselTrack.style.transform = 'translateX(0)';
    });

    // Generate binding rings
    function generateRings() {
        if (!bindingArea) return;
        bindingArea.innerHTML = '';
        for(let i=0; i<28; i++) {
            const hole = document.createElement('div');
            hole.className = 'hole';
            const ring = document.createElement('div');
            ring.className = 'ring';
            hole.appendChild(ring);
            bindingArea.appendChild(hole);
        }
    }
    generateRings();
    window.addEventListener('resize', generateRings);

    // Current filter state
    let currentFilter = 'all'; // 'all' or 'YYYY-M'
    let currentBranchFilter = 'all'; // 'all' or owner name
    let currentYear = new Date().getFullYear() + 543;
    let parsedEventsList = [];

    // Elements
    const branchFiltersContainer = document.getElementById('branch-filters');

    // Parse events into structured cards
    async function loadEvents() {
        try {
            const response = await fetch('/api/events');
            const eventsData = await response.json();
            window.allEvents = eventsData;
            
            parsedEventsList = [];
            eventsData.forEach(event => {
                const dateStr = event.date;
                if (!dateStr || dateStr.trim() === '') return;
                
                let isRange = dateStr.includes('-');
                let parts = isRange ? dateStr.split('-') : [dateStr];
                
                const extractDate = (str) => {
                    let day = null, month = null, year = null;
                    
                    // 1. Identify Month
                    for (let i = 0; i < thaiMonthsAbbr.length; i++) {
                        if (str.includes(thaiMonthsAbbr[i]) || str.includes(thaiMonthsFull[i])) {
                            month = i;
                            break;
                        }
                    }

                    // 2. Identify Numbers
                    let nums = str.match(/\d+/g) || [];
                    
                    // Try to find year first
                    nums.forEach(n => {
                        let val = parseInt(n);
                        if (val >= 2500 && val <= 2600) { // Thai Year (e.g. 2569)
                            year = val;
                        } else if (val >= 2000 && val <= 2100) { // Christian Year (e.g. 2026)
                            year = val + 543;
                        } else if (val >= 60 && val <= 99) { // 2-digit Thai Year (e.g. 69)
                            year = val + 2500;
                        }
                    });

                    // Assign remaining numbers to day and year
                    nums.forEach(n => {
                        let val = parseInt(n);
                        // Skip if this number was already identified as the year
                        if (val === year || val === (year - 2500) || val === (year - 543)) return;
                        
                        if (day === null && val <= 31) {
                            day = val;
                        } else if (year === null) {
                            // Fallback for year if not found yet
                            if (val > 100) year = val > 2000 ? (val < 2500 ? val + 543 : val) : val + 2500;
                            else year = val + 2500;
                        }
                    });

                    return { day, month, year };
                };

                let start = extractDate(parts[0]);
                let end = isRange ? extractDate(parts[1]) : null;
                
                if (isRange && end) {
                    if (start.month === null) start.month = end.month;
                    if (start.year === null) start.year = end.year;
                    if (end.year === null) end.year = start.year;
                }

                // Default year
                if (start.year === null) start.year = currentYear;

                parsedEventsList.push({
                    originalDate: dateStr,
                    start: start,
                    end: end,
                    title: event.title,
                    status: event.status || 'รอการดำเนินการ',
                    owner: event.owner || 'สโมสรนักศึกษา'
                });
            });

            buildMonthFilters();
            buildBranchFilters();
            renderCards();
        } catch(e) {
            console.error(e);
            cardsContainer.innerHTML = '<div class="no-events">ไม่สามารถดึงข้อมูลกิจกรรมได้ กรุณาตรวจสอบว่าเปิด Server แล้วหรือยัง</div>';
        }
    }

    // Build dynamic month filters
    function buildMonthFilters() {
        monthFiltersContainer.innerHTML = '';
        
        let allBtn = document.createElement('button');
        allBtn.className = 'month-btn' + (currentFilter === 'all' ? ' active' : '');
        allBtn.setAttribute('data-filter', 'all');
        allBtn.textContent = 'ทุกเดือน';
        monthFiltersContainer.appendChild(allBtn);

        // Find unique Year-Month combinations
        let yearMonths = new Set();
        parsedEventsList.forEach(e => {
            if (e.start && e.start.month !== null && e.start.year !== null) {
                yearMonths.add(`${e.start.year}-${e.start.month}`);
            }
            if (e.end && e.end.month !== null && e.end.year !== null) {
                yearMonths.add(`${e.end.year}-${e.end.month}`);
            }
        });

        // Convert to array and sort chronologically
        let sortedYM = Array.from(yearMonths).map(ym => {
            let [y, m] = ym.split('-');
            return { year: parseInt(y), month: parseInt(m) };
        }).sort((a, b) => {
            if (a.year !== b.year) return a.year - b.year;
            return a.month - b.month;
        });

        sortedYM.forEach(ym => {
            let btn = document.createElement('button');
            btn.className = 'month-btn' + (currentFilter === `${ym.year}-${ym.month}` ? ' active' : '');
            btn.setAttribute('data-filter', `${ym.year}-${ym.month}`);
            btn.textContent = `${thaiMonthsFull[ym.month]} ${ym.year}`;
            monthFiltersContainer.appendChild(btn);
        });

        // Add event listeners
        const btns = monthFiltersContainer.querySelectorAll('.month-btn');
        btns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                btns.forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
                currentFilter = e.target.getAttribute('data-filter');
                renderCards();
            });
        });
    }

    // Build dynamic branch filters
    function buildBranchFilters() {
        branchFiltersContainer.innerHTML = '';
        
        const allBranches = [
            'คณะวิทยาศาสตร์และเทคโนโลยี',
            'สโมสรนักศึกษา',
            'สาขาวิชาเคมี',
            'สาขาวิชาฟิสิกส์',
            'สาขาวิชาชีววิทยา',
            'สาขาวิชาคณิตศาสตร์',
            'สาขาวิชาวิทยาศาสตร์สิ่งแวดล้อม',
            'สาขาวิชาวิทยาการคอมพิวเตอร์',
            'สาขาวิชาสาธารณสุขศาสตร์',
            'สาขาวิชาเทคโนโลยีคอมพิวเตอร์และดิจิทัล',
            'สาขาวิชาวิทยาการข้อมูล'
        ];

        let allBtn = document.createElement('button');
        allBtn.className = 'branch-btn' + (currentBranchFilter === 'all' ? ' active' : '');
        allBtn.setAttribute('data-branch', 'all');
        allBtn.textContent = 'ทุกสาขา/คณะ';
        branchFiltersContainer.appendChild(allBtn);

        // University Filter Button
        let uniBtn = document.createElement('button');
        uniBtn.className = 'branch-btn' + (currentBranchFilter === 'university' ? ' active' : '');
        uniBtn.setAttribute('data-branch', 'university');
        uniBtn.innerHTML = '<i class="fa-solid fa-building-columns"></i> มหาวิทยาลัย';
        // Special styling for university button
        if (currentBranchFilter === 'university') {
            uniBtn.style.background = '#dc2626';
            uniBtn.style.color = 'white';
            uniBtn.style.borderColor = '#dc2626';
        } else {
            uniBtn.style.background = '#fef2f2';
            uniBtn.style.color = '#991b1b';
            uniBtn.style.borderColor = '#fee2e2';
        }
        branchFiltersContainer.appendChild(uniBtn);

        allBranches.forEach(owner => {
            let btn = document.createElement('button');
            btn.className = 'branch-btn' + (currentBranchFilter === owner ? ' active' : '');
            btn.setAttribute('data-branch', owner);
            btn.textContent = owner.replace('สาขาวิชา', '').replace('คณะวิทยาศาสตร์และเทคโนโลยี', 'คณะวิทย์ฯ');
            branchFiltersContainer.appendChild(btn);
        });

        // Add event listeners
        const btns = branchFiltersContainer.querySelectorAll('.branch-btn');
        btns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const target = e.currentTarget;
                btns.forEach(b => {
                    b.classList.remove('active');
                    // Reset university button if not selected
                    if (b.getAttribute('data-branch') === 'university') {
                        b.style.background = '#fef2f2';
                        b.style.color = '#991b1b';
                    }
                });
                
                target.classList.add('active');
                // Apply active style if university
                if (target.getAttribute('data-branch') === 'university') {
                    target.style.background = '#dc2626';
                    target.style.color = 'white';
                }
                
                currentBranchFilter = target.getAttribute('data-branch');
                renderCards();
            });
        });
    }

    function renderCards() {
        cardsContainer.innerHTML = '';
        
        let displayEvents = parsedEventsList;
        
        // Filter by Month
        if (currentFilter !== 'all') {
            let [filterY, filterM] = currentFilter.split('-');
            filterY = parseInt(filterY);
            filterM = parseInt(filterM);

            displayEvents = displayEvents.filter(e => {
                let startM = e.start.month;
                let startY = e.start.year;
                let endM = e.end ? e.end.month : startM;
                let endY = e.end ? e.end.year : startY;
                
                if (startM === null && endM === null) return true; // All year events

                // Check if the filtered year/month falls within the event's range
                let filterValue = filterY * 12 + filterM;
                
                if (startM !== null && endM !== null) {
                    let startValue = startY * 12 + startM;
                    let endValue = endY * 12 + endM;
                    return filterValue >= startValue && filterValue <= endValue;
                } else if (startM !== null) {
                    let startValue = startY * 12 + startM;
                    return filterValue === startValue;
                }
                return false;
            });
        }

        // Filter by Branch/Owner
        if (currentBranchFilter !== 'all') {
            if (currentBranchFilter === 'university') {
                displayEvents = displayEvents.filter(e => e.category === 'กิจกรรมมหาวิทยาลัย');
            } else {
                displayEvents = displayEvents.filter(e => e.owner === currentBranchFilter);
            }
        }

        if (displayEvents.length === 0) {
            cardsContainer.innerHTML = '<div class="no-events">ไม่พบกิจกรรมในเดือนนี้</div>';
            return;
        }

        displayEvents.forEach(evt => {
            const card = document.createElement('div');
            card.className = 'event-card';

            let monthIndex = evt.start.month !== null ? evt.start.month : 0;
            let colorClass = `bg-m${(monthIndex % 5) + 1}`;

            let dateBoxHtml = '';
            let startYear = evt.start.year || currentYear;
            let endYear = evt.end && evt.end.year ? evt.end.year : startYear;

            if (evt.start.day === null && evt.start.month !== null) {
                dateBoxHtml = `
                    <div class="date-month" style="font-size:14px;">ตลอดเดือน</div>
                    <div class="date-large" style="font-size:18px; margin-top:4px;">${thaiMonthsFull[evt.start.month]} ${startYear}</div>
                `;
            } else if (evt.start.day === null && evt.start.month === null) {
                dateBoxHtml = `
                    <div class="date-month" style="font-size:14px;">ตลอดปี</div>
                    <div class="date-large" style="font-size:24px;">${startYear}</div>
                `;
            } else if (!evt.end || (evt.start.day === evt.end.day && evt.start.month === evt.end.month && evt.start.year === evt.end.year)) {
                let monthStr = evt.start.month !== null ? thaiMonthsAbbr[evt.start.month] : '';
                dateBoxHtml = `
                    <div class="date-large">${evt.start.day || ''}</div>
                    <div class="date-month" style="font-size:13px;">${monthStr} ${startYear}</div>
                `;
            } else {
                let startMonthStr = evt.start.month !== null ? thaiMonthsAbbr[evt.start.month] : '';
                let endMonthStr = (evt.end.month !== null && evt.end.month !== evt.start.month) ? thaiMonthsAbbr[evt.end.month] : startMonthStr;
                
                dateBoxHtml = `
                    <div class="date-large" style="font-size: 20px;">${evt.start.day || ''} <span style="font-size:11px">${startMonthStr} ${startYear}</span></div>
                    <div class="date-to">ถึง</div>
                    <div class="date-large" style="font-size: 20px;">${evt.end.day || ''} <span style="font-size:11px">${endMonthStr} ${endYear}</span></div>
                `;
            }

            let cleanTitle = evt.title.replace(/\*$/, '');

            let categoryBadge = '';
            if (evt.category === 'กิจกรรมมหาวิทยาลัย') {
                categoryBadge = `<span style="font-size: 10px; background: #dc2626; color: white; padding: 2px 8px; border-radius: 4px; margin-bottom: 5px; display: inline-block; font-weight: bold;">กิจกรรมมหาวิทยาลัย</span><br>`;
            }

            let statusClass = evt.status === 'เสร็จสิ้น' ? 'status-done' : 'status-pending';

            card.innerHTML = `
                <div class="card-date-box ${colorClass}">
                    ${dateBoxHtml}
                </div>
                <div class="card-content">
                    <div class="card-body">
                        ${categoryBadge}${cleanTitle}
                    </div>
                    <div class="card-footer">
                        <div class="${statusClass}"><i class="fa-solid fa-check-circle"></i> ${evt.status}</div>
                        <div class="card-owner"><i class="fa-solid fa-tag"></i> ${evt.owner}</div>
                    </div>
                </div>
            `;
            cardsContainer.appendChild(card);
        });
    }

    // Init
    loadEvents();
    loadCarousel();
    generateRings();
    checkAuth();
    initLeaderboardTicker();
});

// --- Auth Logic ---
let currentUser = null;

async function checkAuth() {
    try {
        const res = await fetch('/api/me');
        if (res.ok) {
            const data = await res.json();
            currentUser = data.user;
        } else {
            currentUser = null;
        }
        renderUserControls();
    } catch(e) {
        console.error("Auth check failed");
    }
}

function renderUserControls() {
    const controls = document.getElementById('user-controls');
    if (!controls) return;
    
    if (currentUser) {
        let badgeColor = currentUser.role === 'admin' ? '#ef4444' : (currentUser.role === 'major' ? '#f59e0b' : '#10b981');
        
        let profileBtn = '';
        if (currentUser.role === 'student') {
            profileBtn = `<a href="/profile" style="background: none; border: none; color: #0284c7; cursor: pointer; font-family: 'Kanit', sans-serif; font-weight: 500; font-size: 13px; margin-right: 10px; border-right: 1px solid #e2e8f0; padding-right: 10px; text-decoration: none;">โปรไฟล์ของฉัน</a>`;
        }
        
        controls.innerHTML = `
            <div style="display: flex; align-items: center; gap: 8px;">
                <button onclick="shareWebsite()" style="background: white; border: none; width: 34px; height: 34px; border-radius: 50%; box-shadow: 0 2px 5px rgba(0,0,0,0.1); cursor: pointer; color: #0284c7; display: flex; align-items: center; justify-content: center; transition: 0.2s;" title="แชร์เว็บไซต์">
                    <i class="fa-solid fa-share-nodes"></i>
                </button>
                <div style="background: white; padding: 6px 12px; border-radius: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); display: flex; align-items: center; gap: 10px; font-size: 14px;">
                    <span><i class="fa-solid fa-user" style="color: ${badgeColor};"></i> สวัสดี, <strong>${currentUser.name}</strong></span>
                    ${profileBtn}
                    <button onclick="doLogout()" style="background: none; border: none; color: #dc2626; cursor: pointer; font-family: 'Kanit', sans-serif; font-weight: 500; font-size: 13px;">ออกจากระบบ</button>
                </div>
            </div>
        `;
    } else {
        controls.innerHTML = `
            <div style="display: flex; align-items: center; gap: 8px;">
                <button onclick="shareWebsite()" style="background: white; border: none; width: 34px; height: 34px; border-radius: 50%; box-shadow: 0 2px 5px rgba(0,0,0,0.1); cursor: pointer; color: #0284c7; display: flex; align-items: center; justify-content: center; transition: 0.2s;" title="แชร์เว็บไซต์">
                    <i class="fa-solid fa-share-nodes"></i>
                </button>
                <a href="/login" style="background: white; padding: 8px 16px; border: none; border-radius: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); cursor: pointer; font-family: 'Kanit', sans-serif; font-weight: 500; font-size: 14px; color: #0284c7; display: flex; align-items: center; gap: 8px; text-decoration: none;">
                    <i class="fa-solid fa-right-to-bracket"></i> เข้าสู่ระบบ / สมัครสมาชิก
                </a>
            </div>
        `;
    }
}

async function shareWebsite() {
    const shareData = {
        title: 'ปฏิทินกิจกรรมนักศึกษา 2569',
        text: 'ติดตามกิจกรรมและคะแนนสะสมของนักศึกษา คณะวิทยาศาสตร์และเทคโนโลยี',
        url: window.location.origin
    };

    try {
        if (navigator.share) {
            await navigator.share(shareData);
        } else {
            await navigator.clipboard.writeText(window.location.origin);
            alert('คัดลอกลิงก์เว็บไซต์เรียบร้อยแล้ว!');
        }
    } catch (err) {
        console.log('Error sharing:', err);
    }
}

async function doLogout() {
    try {
        await fetch('/api/logout', {method: 'POST'});
        checkAuth();
        window.location.reload();
    } catch(e) { console.error(e); }
}

async function openPublicLeaderboard() {
    document.getElementById('public-leaderboard-modal').style.display = 'flex';
    const container = document.getElementById('public-leaderboard-list');
    container.innerHTML = '<div style="text-align: center; color: #8b5a2b; font-weight: bold; padding: 20px;">กำลังโหลด...</div>';
    
    try {
        const res = await fetch('/api/leaderboard');
        const data = await res.json();
        
        container.innerHTML = '';
        if (data.length === 0) {
            container.innerHTML = '<div style="text-align: center; padding: 20px; color: #8b5a2b; font-weight: bold;">ยังไม่มีข้อมูลคะแนน</div>';
            return;
        }
        
        data.forEach((student, index) => {
            let rankNum = index + 1;
            let bgColor = "linear-gradient(to bottom, #fde047, #f59e0b)";
            let borderColor = "#b45309";
            
            // Adjust colors for top 3
            if (rankNum === 1) {
                bgColor = "linear-gradient(to bottom, #fef08a, #eab308)"; // Gold
            } else if (rankNum === 2) {
                bgColor = "linear-gradient(to bottom, #e2e8f0, #94a3b8)"; // Silver
                borderColor = "#64748b";
            } else if (rankNum === 3) {
                bgColor = "linear-gradient(to bottom, #fed7aa, #d97706)"; // Bronze
                borderColor = "#92400e";
            }
            
            container.innerHTML += `
                <div style="background: ${bgColor}; border-radius: 50px; padding: 8px 25px 8px 12px; display: flex; align-items: center; justify-content: space-between; border-bottom: 5px solid ${borderColor}; box-shadow: 0 4px 8px rgba(0,0,0,0.2); margin-bottom: 5px;">
                    
                    <div style="display: flex; align-items: center; gap: 15px;">
                        <!-- Rank Coin -->
                        <div style="width: 35px; height: 35px; background: radial-gradient(circle at 30% 30%, #fef08a, #ca8a04); border-radius: 50%; border: 3px solid #a16207; box-shadow: inset -2px -2px 5px rgba(0,0,0,0.3), 2px 2px 5px rgba(0,0,0,0.2); display: flex; align-items: center; justify-content: center; color: #854d0e; font-weight: bold; font-size: 16px;">
                            ${rankNum}
                        </div>
                        
                        <!-- Name & Major -->
                        <div style="display: flex; flex-direction: column;">
                            <div style="color: white; font-weight: 800; font-size: 18px; text-shadow: 2px 2px 4px rgba(0,0,0,0.7);">
                                ${student.name || student.username}
                            </div>
                            <div style="color: rgba(255,255,255,0.95); font-size: 12px; font-weight: 500; text-shadow: 1px 1px 2px rgba(0,0,0,0.6);">
                                ${student.major || '-'}
                            </div>
                        </div>
                    </div>
                    
                    <!-- Score -->
                    <div style="text-align: right;">
                        <div style="color: white; font-weight: 900; font-size: 22px; text-shadow: 2px 2px 4px rgba(0,0,0,0.7);">
                            ${student.score}
                        </div>
                        <div style="color: rgba(255,255,255,0.9); font-size: 10px; font-weight: bold; text-transform: uppercase; text-shadow: 1px 1px 2px rgba(0,0,0,0.5);">คะแนน</div>
                    </div>
                    
                </div>
            `;
        });
    } catch(e) { console.error(e); }
}

function closePublicLeaderboard() {
    document.getElementById('public-leaderboard-modal').style.display = 'none';
}

// --- Leaderboard Ticker Logic ---
let tickerData = [];
let tickerIndex = 0;

async function initLeaderboardTicker() {
    const tickerEl = document.getElementById('leaderboard-ticker');
    const contentEl = document.getElementById('ticker-content');
    if (!tickerEl || !contentEl) return;

    try {
        const res = await fetch('/api/leaderboard');
        tickerData = await res.json();

        if (tickerData && tickerData.length > 0) {
            tickerEl.style.display = 'flex';
            updateTickerContent();
            setInterval(updateTickerContent, 4000); // Cycle every 4 seconds
        }
    } catch (e) { 
        console.error("Ticker error:", e); 
    }
}

function updateTickerContent() {
    const contentEl = document.getElementById('ticker-content');
    if (!contentEl || tickerData.length === 0) return;

    const student = tickerData[tickerIndex];
    const rankNum = tickerIndex + 1;

    // Smooth transition
    contentEl.style.opacity = 0;
    contentEl.style.transform = 'translateY(-5px)';

    setTimeout(() => {
        contentEl.innerHTML = `
            <span style="color: #8b5a2b; font-weight: bold;">อันดับที่ ${rankNum}</span> 
            <span style="color: #d97706; font-weight: 600;">คุณ${student.name}</span> 
            <span style="font-size: 13px; color: #4b5563;">สาขา${student.major || '-'}</span> 
            <span style="margin-left: 8px; background: #f59e0b; color: white; padding: 2px 10px; border-radius: 20px; font-size: 12px; font-weight: bold; box-shadow: 0 2px 4px rgba(245, 158, 11, 0.3);">
                <i class="fa-solid fa-medal"></i> ${student.score} คะแนน
            </span>
        `;
        contentEl.style.opacity = 1;
        contentEl.style.transform = 'translateY(0)';
        
        tickerIndex = (tickerIndex + 1) % Math.min(tickerData.length, 10);
    }, 500);
}
