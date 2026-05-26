// ===== GLOBAL STATE =====
let currentUser = null;
let userRegistrations = new Set();
let carouselImages = [];
let carouselIndex = 0;
let carouselTimer = null;
let _notifIntervalStarted = false;

// Global Mobile Menu Toggle
window.toggleMobileMenu = function() {
    const navRight = document.getElementById('nav-right');
    if (navRight) {
        navRight.classList.toggle('active');
    }
};

// ===== GLOBAL HELPERS =====
function h(text) {
    if (!text) return '';
    return text.toString()
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

document.addEventListener('DOMContentLoaded', () => {
    const cardsContainer = document.getElementById('cards-container');
    const monthFiltersContainer = document.getElementById('month-filters');
    const branchFiltersContainer = document.getElementById('branch-filters');
    const carouselTrack = document.getElementById('carousel-track');

    const thaiMonthsFull = ['มกราคม','กุมภาพันธ์','มีนาคม','เมษายน','พฤษภาคม','มิถุนายน','กรกฎาคม','สิงหาคม','กันยายน','ตุลาคม','พฤศจิกายน','ธันวาคม'];
    const thaiMonthsAbbr = ['ม.ค.','ก.พ.','มี.ค.','เม.ย.','พ.ค.','มิ.ย.','ก.ค.','ส.ค.','ก.ย.','ต.ค.','พ.ย.','ธ.ค.'];

    // JS String Escaping Helper
    function j(text) {
        if (!text) return '';
        return text.toString()
            .replace(/\\/g, "\\\\")
            .replace(/'/g, "\\'")
            .replace(/"/g, "\\\"")
            .replace(/\n/g, "\\n")
            .replace(/\r/g, "\\r");
    }

    // ===== CAROUSEL =====

    async function loadCarousel() {
        try {
            const res = await fetch('/api/carousel');
            carouselImages = await res.json();
            renderCarousel();
            if (carouselImages.length > 1) startCarousel();
        } catch(e) { console.error(e); }
    }

    function renderCarousel() {
        if (!carouselTrack) return;
        carouselTrack.innerHTML = '';
        const dotsEl = document.getElementById('carousel-dots');
        if (dotsEl) dotsEl.innerHTML = '';

        carouselImages.forEach((src, i) => {
            const img = document.createElement('img');
            img.src = src;
            carouselTrack.appendChild(img);

            if (dotsEl) {
                const dot = document.createElement('div');
                dot.className = 'carousel-dot' + (i === 0 ? ' active' : '');
                dotsEl.appendChild(dot);
            }
        });
        // Clone first for seamless loop
        if (carouselImages.length > 1) {
            const clone = document.createElement('img');
            clone.src = carouselImages[0];
            carouselTrack.appendChild(clone);
        }
        // Apply correct width based on current container size
        requestAnimationFrame(updateCarouselWidth);
    }

    function updateCarouselWidth() {
        const container = document.getElementById('carousel-container');
        if (!container) return;
        const w = container.clientWidth;
        carouselTrack.querySelectorAll('img').forEach(img => img.style.width = w + 'px');
        carouselTrack.style.transform = `translateX(-${carouselIndex * w}px)`;
    }

    function startCarousel() {
        if (carouselTimer) clearInterval(carouselTimer);
        carouselTimer = setInterval(advanceCarousel, 4000);
    }

    function advanceCarousel() {
        const container = document.getElementById('carousel-container');
        if (!container) return;
        const w = container.clientWidth;
        carouselIndex++;
        carouselTrack.style.transition = 'transform 0.8s cubic-bezier(0.4,0,0.2,1)';
        carouselTrack.style.transform = `translateX(-${carouselIndex * w}px)`;
        updateDots(carouselIndex % carouselImages.length);

        if (carouselIndex >= carouselImages.length) {
            setTimeout(() => {
                carouselTrack.style.transition = 'none';
                carouselIndex = 0;
                carouselTrack.style.transform = 'translateX(0)';
                updateDots(0);
                setTimeout(() => { carouselTrack.style.transition = 'transform 0.8s cubic-bezier(0.4,0,0.2,1)'; }, 30);
            }, 820);
        }
    }

    function updateDots(activeIndex) {
        const dots = document.querySelectorAll('.carousel-dot');
        dots.forEach((d, i) => d.classList.toggle('active', i === activeIndex));
    }

    window.addEventListener('resize', () => {
        updateCarouselWidth();
    });

    // ===== FILTER STATE =====
    let currentYear = new Date().getFullYear() + 543;
    let currentMonth = new Date().getMonth();
    let currentFilter = `${currentYear}-${currentMonth}`;
    let currentBranchFilter = 'all';
    let currentSearchText = '';
    let renderedCount = 12;
    const cardsPerPage = 12;
    let infiniteScrollObserver = null;
    let parsedEventsList = [];
    let currentView = 'grid';
    let searchTimeout = null;

    // ===== LOAD EVENTS =====
    async function loadEvents() {
        try {
            const response = await fetch('/api/events');
            const eventsDataRaw = await response.json();
            const eventsData = Array.isArray(eventsDataRaw) ? eventsDataRaw : (eventsDataRaw.events || []);
            window.allEvents = eventsData;
            parsedEventsList = [];

            eventsData.forEach(event => {
                // Skip hidden events on public page
                if (event.hidden === true) return;

                const dateStr = event.date;
                if (!dateStr || !dateStr.trim()) return;

                let isRange = dateStr.includes('-');
                let parts = isRange ? dateStr.split('-') : [dateStr];

                const extractDate = (str) => {
                    let day = null, month = null, year = null;
                    for (let i = 0; i < thaiMonthsAbbr.length; i++) {
                        if (str.includes(thaiMonthsAbbr[i]) || str.includes(thaiMonthsFull[i])) { month = i; break; }
                    }
                    let nums = str.match(/\d+/g) || [];
                    nums.forEach(n => {
                        let val = parseInt(n);
                        if (val >= 2500 && val <= 2600) year = val;
                        else if (val >= 2000 && val <= 2100) year = val + 543;
                        else if (val >= 60 && val <= 99) year = val + 2500;
                    });
                    nums.forEach(n => {
                        let val = parseInt(n);
                        if (val === year || val === (year-2500) || val === (year-543)) return;
                        if (day === null && val <= 31) day = val;
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
                if (start.year === null) start.year = currentYear;

                parsedEventsList.push({
                    id: event.id,
                    originalDate: dateStr, start, end,
                    title: event.title, status: event.status || 'รอการดำเนินการ',
                    owner: event.owner || 'สโมสรนักศึกษา',
                    category: event.category || '',
                    location: event.location || '',
                    description: event.description || '',
                    registration_open: event.registration_open || false,
                    max_participants: event.max_participants || 0,
                    registered_count: event.registered_count || 0,
                    createdAt: event.created_at || ''
                });
            });

            buildMonthFilters();
            buildBranchFilters();
            renderCards();
        } catch(e) {
            console.error(e);
            cardsContainer.innerHTML = '<div class="no-events"><div class="no-events-icon"><i class="fa-solid fa-circle-exclamation"></i></div><h3>ไม่สามารถโหลดข้อมูลได้</h3><p>กรุณาตรวจสอบว่าเซิร์ฟเวอร์เปิดอยู่ แล้วลองรีเฟรชหน้าใหม่</p></div>';
        }
    }

    // ===== BUILD MONTH FILTERS =====
    function buildMonthFilters() {
        monthFiltersContainer.innerHTML = '';
        const allBtn = makeFilterBtn('ทุกเดือน', 'all', currentFilter === 'all', 'month');
        monthFiltersContainer.appendChild(allBtn);

        let yearMonths = new Set();
        parsedEventsList.forEach(e => {
            if (e.start && e.start.month !== null && e.start.year !== null)
                yearMonths.add(`${e.start.year}-${e.start.month}`);
        });

        [...yearMonths].map(ym => {
            let [y, m] = ym.split('-');
            return { year: parseInt(y), month: parseInt(m) };
        }).sort((a, b) => a.year !== b.year ? a.year - b.year : a.month - b.month)
        .forEach(ym => {
            const btn = makeFilterBtn(
                `${thaiMonthsFull[ym.month]} ${ym.year}`,
                `${ym.year}-${ym.month}`,
                currentFilter === `${ym.year}-${ym.month}`,
                'month'
            );
            monthFiltersContainer.appendChild(btn);
        });
    }

    // ===== BUILD BRANCH FILTERS =====
    function buildBranchFilters() {
        branchFiltersContainer.innerHTML = '';
        
        // 1. Standard branches to always show (from users.json)
        const standardBranches = [
            'สาขาวิชาเคมี', 'สาขาวิชาฟิสิกส์', 'สาขาวิชาชีววิทยา',
            'สาขาวิชาคณิตศาสตร์', 'สาขาวิชาสถิติ', 'สาขาวิชาวิทยาการคอมพิวเตอร์', 
            'สาขาวิชาเทคโนโลยีสารสนเทศ', 'สาขาวิชาวิทยาศาสตร์สิ่งแวดล้อม', 
            'สาขาวิชาคหกรรมศาสตร์', 'สาขาวิชาสาธารณสุขศาสตร์'
        ];

        // 2. Dynamic branches from data
        const uniqueOwners = new Set();
        parsedEventsList.forEach(e => {
            if (e.owner && e.owner !== 'แอดมินส่วนกลาง' && e.owner !== 'สโมสรนักศึกษา' && !standardBranches.includes(e.owner)) {
                if (e.owner !== 'คณะวิทยาศาสตร์และเทคโนโลยี') uniqueOwners.add(e.owner);
            }
        });

        const allBranches = [...standardBranches, ...Array.from(uniqueOwners)].sort();
        const primaryBranches = ['คณะวิทยาศาสตร์และเทคโนโลยี', 'สโมสรนักศึกษา'];
        
        branchFiltersContainer.appendChild(makeFilterBtn('ทุกสาขา', 'all', currentBranchFilter === 'all', 'branch'));

        // University special button
        const uniBtn = makeFilterBtn('🏛 มหาวิทยาลัย', 'university', currentBranchFilter === 'university', 'branch');
        uniBtn.classList.add('uni-style');
        branchFiltersContainer.appendChild(uniBtn);

        // Add primary ones
        primaryBranches.forEach(owner => {
            const label = owner.replace('สาขาวิชา', '').replace('คณะวิทยาศาสตร์และเทคโนโลยี', 'คณะวิทย์ฯ');
            branchFiltersContainer.appendChild(makeFilterBtn(label, owner, currentBranchFilter === owner, 'branch'));
        });

        // Add the rest
        allBranches.forEach(owner => {
            if (!primaryBranches.includes(owner)) {
                const label = owner.replace('สาขาวิชา', '').replace('คณะวิทยาศาสตร์และเทคโนโลยี', 'คณะวิทย์ฯ');
                branchFiltersContainer.appendChild(makeFilterBtn(label, owner, currentBranchFilter === owner, 'branch'));
            }
        });
    }

    function makeFilterBtn(label, value, isActive, type) {
        const btn = document.createElement('button');
        btn.className = 'filter-btn' + (isActive ? ` active-${type}` : '');
        btn.innerHTML = label;
        btn.setAttribute('data-value', value);
        btn.addEventListener('click', () => {
            if (type === 'month') {
                monthFiltersContainer.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active-month'));
                btn.classList.add('active-month');
                currentFilter = value;
            } else {
                branchFiltersContainer.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active-branch'));
                btn.classList.add('active-branch');
                currentBranchFilter = value;
            }
            renderCards(false);
        });
        return btn;
    }

    // ===== RENDER CARDS =====
    // window.setView logic is handled globally below

    function renderCards(append = false) {
        const isCalendar = currentView === 'calendar';
        cardsContainer.style.display = isCalendar ? 'none' : 'grid';
        document.getElementById('calendar-view').style.display = isCalendar ? 'block' : 'none';
        
        if (isCalendar) {
            renderCalendar();
            return;
        }

        if (!append) {
            cardsContainer.innerHTML = '';
            renderedCount = cardsPerPage;
            cardsContainer.className = 'cards-container' + (currentView === 'list' ? ' list-view' : '');
        }

        let displayEvents = [...parsedEventsList];
        
        // Define today's values
        const now = new Date();
        const tDay = now.getDate();
        const tMonth = now.getMonth();
        const tYear = now.getFullYear() + 543;

        // Sorting logic: Today > Chronological > Newest Created
        displayEvents.sort((a, b) => {
            const isTodayA = a.start.day === tDay && a.start.month === tMonth && a.start.year === tYear;
            const isTodayB = b.start.day === tDay && b.start.month === tMonth && b.start.year === tYear;
            
            // 1. Today's events always first
            if (isTodayA && !isTodayB) return -1;
            if (!isTodayA && isTodayB) return 1;

            // 2. Sort by Year
            if (a.start.year !== b.start.year) {
                if (a.start.year === null) return 1;
                if (b.start.year === null) return -1;
                return a.start.year - b.start.year;
            }
            // 3. Sort by Month
            if (a.start.month !== b.start.month) {
                if (a.start.month === null) return 1;
                if (b.start.month === null) return -1;
                return a.start.month - b.start.month;
            }
            // 4. Sort by Day
            if (a.start.day !== b.start.day) {
                if (a.start.day === null) return 1;
                if (b.start.day === null) return -1;
                return a.start.day - b.start.day;
            }

            // 5. Same day? Newest created first
            if (a.createdAt && b.createdAt) {
                return b.createdAt.localeCompare(a.createdAt);
            }
            return 0;
        });

        // Filter logic (Search)
        if (currentSearchText) {
            const q = currentSearchText.toLowerCase();
            displayEvents = displayEvents.filter(e => e.title.toLowerCase().includes(q));
        }

        // Filter logic (Month)
        if (currentFilter !== 'all') {
            let [filterY, filterM] = currentFilter.split('-').map(Number);
            displayEvents = displayEvents.filter(e => {
                let sM = e.start.month, sY = e.start.year;
                let eM = e.end ? e.end.month : sM, eY = e.end ? e.end.year : sY;
                if (sM === null) return true;
                let fv = filterY * 12 + filterM;
                return fv >= sY * 12 + sM && fv <= eY * 12 + eM;
            });
        }

        // Filter logic (Branch)
        if (currentBranchFilter !== 'all') {
            if (currentBranchFilter === 'university')
                displayEvents = displayEvents.filter(e => e.category === 'กิจกรรมมหาวิทยาลัย');
            else
                displayEvents = displayEvents.filter(e => e.owner === currentBranchFilter);
        }

        const totalToDisplay = displayEvents.length;
        const countEl = document.getElementById('results-count');
        if (countEl) countEl.innerHTML = `พบ <strong>${totalToDisplay}</strong> กิจกรรม`;

        const currentSlice = displayEvents.slice(append ? renderedCount : 0, append ? renderedCount + cardsPerPage : cardsPerPage);
        
        if (append) renderedCount += cardsPerPage;

        if (totalToDisplay === 0) {
            const monthName = currentFilter !== 'all' ? thaiMonthsFull[parseInt(currentFilter.split('-')[1])] : '';
            const msg = monthName ? `ยังไม่มีกิจกรรมในเดือน${monthName}` : 'ไม่พบกิจกรรมที่ตรงกับเงื่อนไข';
            const sub = monthName ? 'ติดตามกิจกรรมใหม่ได้เร็วๆ นี้ หรือลองเลือกเดือนอื่น' : 'ลองเปลี่ยนเดือนหรือสาขาวิชาที่ต้องการค้นหา';
            cardsContainer.innerHTML = `<div class="no-events"><div class="no-events-icon"><i class="fa-solid fa-calendar-xmark"></i></div><h3>${msg}</h3><p>${sub}</p></div>`;
            document.getElementById('loading-more').style.display = 'none';
            return;
        }

        currentSlice.forEach((evt, idx) => {
            const cardIdx = append ? (renderedCount - cardsPerPage + idx) : idx;
            const card = document.createElement('div');
            card.className = 'event-card';
            card.style.animationDelay = `${Math.min(idx * 0.05, 0.5)}s`;

            let monthIndex = evt.start.month !== null ? evt.start.month : 0;
            let colorClass = `bg-m${(monthIndex % 5) + 1}`;
            
            let dateHtml = '';
            if (evt.start.day === null) {
                dateHtml = `<div class="date-small">ตลอดเดือน</div><div class="date-large">${thaiMonthsAbbr[monthIndex]}</div>`;
            } else if (!evt.end || (evt.start.day === evt.end.day && evt.start.month === evt.end.month)) {
                dateHtml = `<div class="date-large">${evt.start.day}</div><div class="date-small">${thaiMonthsAbbr[monthIndex]}</div>`;
            } else {
                // Range view: Show month abbreviation below the days to avoid confusion
                dateHtml = `<div class="date-range-nums"><span>${evt.start.day}</span><i class="fa-solid fa-arrow-right-long"></i><span>${evt.end.day}</span></div><div class="date-small">${thaiMonthsAbbr[monthIndex]}</div>`;
            }

            let catClass = 'cat-club';
            let catLabel = 'ชมรม/ทั่วไป';
            if (evt.category === 'กิจกรรมมหาวิทยาลัย') {
                catClass = 'cat-uni';
                catLabel = 'มหาวิทยาลัย';
            } else if ((evt.owner && (evt.owner.includes('สาขาวิชา') || evt.owner.includes('คณะ'))) || evt.category === 'กิจกรรมสาขาวิชา') {
                catClass = 'cat-major';
                catLabel = 'คณะ/สาขา';
            }

            let progressWidth = 0;
            let barClass = '';
            if (evt.max_participants > 0) {
                progressWidth = Math.min((evt.registered_count / evt.max_participants) * 100, 100);
                if (progressWidth >= 100) barClass = 'full';
                else if (progressWidth >= 80) barClass = 'warning';
            }

            const isRegistered = userRegistrations.has(evt.id);
            const isFull = evt.max_participants > 0 && evt.registered_count >= evt.max_participants;
            const isToday = evt.start.day === tDay && evt.start.month === tMonth && evt.start.year === tYear;
            
            let btnHtml = '';
            // Auto-enable registration if it's today's event, unless it's explicitly finished
            if (evt.registration_open || (isToday && evt.status !== 'เสร็จสิ้น')) {
                let btnText = 'จองกิจกรรม';
                let btnClass = 'reg-btn nav-btn-blue';
                if (isRegistered) {
                    btnText = '<i class="fa-solid fa-check-circle"></i> จองแล้ว';
                    btnClass = 'reg-btn registered';
                } else if (isFull) {
                    btnText = 'สำรองที่นั่ง';
                    btnClass = 'reg-btn nav-btn-amber';
                }
                btnHtml = `<button class="${btnClass}" onclick="event.stopPropagation(); openRegisterConfirm('${j(evt.id)}', '${j(evt.title)}')">${btnText}</button>`;
            }

            const todayBadge = isToday ? '<span class="today-badge"><i class="fa-solid fa-star"></i> วันนี้</span>' : '';

            card.innerHTML = `
                <div class="card-date-side ${colorClass}">${dateHtml}</div>
                <div class="card-main">
                    <span class="category-badge ${catClass}">${catLabel}</span>
                    <h3 class="event-title">${h(evt.title.replace(/\*$/, ''))}${todayBadge}</h3>
                    <div class="event-info-item"><i class="fa-solid fa-location-dot"></i><span>${evt.location || 'คณะวิทยาศาสตร์ฯ'}</span></div>
                    <div class="event-info-item"><i class="fa-solid fa-graduation-cap"></i><span>${evt.owner || 'สโมสรนักศึกษา'}</span></div>
                    <div class="capacity-container">
                        <div class="capacity-label">
                            <span>ความจุที่นั่ง</span>
                            <span>${evt.max_participants > 0 ? `${evt.registered_count}/${evt.max_participants}` : 'ไม่จำกัด'}</span>
                        </div>
                        <div class="capacity-bar">
                            <div class="capacity-progress ${barClass}" style="width: ${progressWidth}%"></div>
                        </div>
                    </div>
                </div>
                <div class="card-actions">
                    <div style="flex:1">
                        <span class="status-badge ${evt.status==='เสร็จสิ้น'?'status-done':'status-pending'}">${evt.status || 'รอการดำเนินการ'}</span>
                    </div>
                    ${btnHtml}
                </div>`;

            card.style.cursor = 'pointer';
            card.addEventListener('click', (e) => {
                if (e.target.closest('button')) return;
                openEventDetail(evt);
            });
            cardsContainer.appendChild(card);
        });

        setupInfiniteScroll(totalToDisplay);
    }

    function setupInfiniteScroll(total) {
        const loadingEl = document.getElementById('loading-more');
        if (infiniteScrollObserver) infiniteScrollObserver.disconnect();
        
        if (renderedCount >= total) {
            if (loadingEl) loadingEl.style.display = 'none';
            return;
        }

        infiniteScrollObserver = new IntersectionObserver((entries) => {
            if (entries[0].isIntersecting) {
                if (loadingEl) loadingEl.style.display = 'block';
                // Use a small timeout to simulate loading and prevent accidental double triggers
                setTimeout(() => {
                    if (renderedCount < total) {
                        renderCards(true);
                    }
                }, 300);
            }
        }, { threshold: 0.1, rootMargin: '100px' });

        const sentinel = document.getElementById('scroll-sentinel');
        if (sentinel) infiniteScrollObserver.observe(sentinel);
    }

    function renderCalendar() {
        const grid = document.getElementById('calendar-grid');
        const monthTitle = document.getElementById('calendar-month-name');
        grid.innerHTML = '';
        
        let targetY, targetM;
        if (currentFilter === 'all') {
            targetY = currentYear; targetM = currentMonth;
        } else {
            [targetY, targetM] = currentFilter.split('-').map(Number);
        }
        
        monthTitle.textContent = `${thaiMonthsFull[targetM]} ${targetY}`;
        
        // Headers
        const days = ['อา.', 'จ.', 'อ.', 'พ.', 'พฤ.', 'ศ.', 'ส.'];
        days.forEach(d => {
            const h = document.createElement('div');
            h.className = 'cal-day-header';
            h.textContent = d;
            grid.appendChild(h);
        });
        
        const firstDay = new Date(targetY, targetM, 1).getDay();
        const daysInMonth = new Date(targetY, targetM + 1, 0).getDate();
        
        // Padding
        for (let i = 0; i < firstDay; i++) {
            const empty = document.createElement('div');
            empty.className = 'cal-day';
            grid.appendChild(empty);
        }
        
        // Days
        for (let d = 1; d <= daysInMonth; d++) {
            const dayEl = document.createElement('div');
            const isToday = d === new Date().getDate() && targetM === new Date().getMonth() && targetY === new Date().getFullYear();
            
            // Events for this day
            const dayEvents = parsedEventsList.filter(e => {
                if (e.start.day === null) return false;
                if (e.start.year !== targetY || e.start.month !== targetM) return false;
                
                // Apply search filter if present
                if (currentSearchText) {
                    const q = currentSearchText.toLowerCase();
                    if (!e.title.toLowerCase().includes(q)) return false;
                }
                
                // Apply branch filter if present
                if (currentBranchFilter !== 'all') {
                    if (currentBranchFilter === 'university') {
                        if (e.category !== 'กิจกรรมมหาวิทยาลัย') return false;
                    } else {
                        if (e.owner !== currentBranchFilter) return false;
                    }
                }
                
                if (!e.end) return e.start.day === d;
                return d >= e.start.day && d <= e.end.day;
            });
            
            const hasEvents = dayEvents.length > 0;
            dayEl.className = 'cal-day' + (isToday ? ' today' : '') + (hasEvents ? ' has-events' : '');
            dayEl.innerHTML = `<div class="cal-day-num">${d}</div>`;
            
            dayEvents.forEach(e => {
                const tag = document.createElement('div');
                tag.className = 'cal-event-tag';
                tag.textContent = e.title.replace(/\*$/, '');
                tag.onclick = (ev) => {
                    ev.stopPropagation();
                    openEventDetail(e);
                };
                dayEl.appendChild(tag);
            });
            
            if (hasEvents) {
                let hideTimeout = null;
                const popover = document.getElementById('calendar-popover');
                
                const showPopover = (ev) => {
                    clearTimeout(hideTimeout);
                    if (!popover) return;
                    
                    // Build popover content
                    let eventsHtml = '';
                    dayEvents.forEach(e => {
                        let catLabel = 'ชมรม/ทั่วไป';
                        let catClass = 'cat-club';
                        if (e.category === 'กิจกรรมมหาวิทยาลัย') {
                            catLabel = 'มหาวิทยาลัย';
                            catClass = 'cat-uni';
                        } else if ((e.owner && (e.owner.includes('สาขาวิชา') || e.owner.includes('คณะ'))) || e.category === 'กิจกรรมสาขาวิชา') {
                            catLabel = 'คณะ/สาขา';
                            catClass = 'cat-major';
                        }
                        
                        eventsHtml += `
                            <div class="popover-item">
                                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 4px;">
                                    <span class="category-badge ${catClass}" style="font-size:8px; padding: 2px 8px; margin-bottom:0;">${catLabel}</span>
                                    <span style="font-size:9px; color:var(--primary); font-weight:700;">⭐ ${e.max_participants > 0 ? `${e.registered_count}/${e.max_participants}` : 'ไม่จำกัด'}</span>
                                </div>
                                <div class="popover-item-title">${h(e.title.replace(/\*$/, ''))}</div>
                                <div class="popover-item-meta">
                                    <span><i class="fa-solid fa-location-dot"></i> ${h(e.location || 'คณะวิทยาศาสตร์ฯ')}</span>
                                </div>
                            </div>
                        `;
                    });
                    
                    popover.innerHTML = `
                        <div class="popover-header">
                            <span>📅 กิจกรรมวันที่ ${d} ${thaiMonthsFull[targetM]}</span>
                            <span style="font-size:10px; color:var(--slate-400);">${dayEvents.length} รายการ</span>
                        </div>
                        <div class="popover-list">${eventsHtml}</div>
                    `;
                    
                    // Add click event listener to popover items to open details
                    popover.querySelectorAll('.popover-item').forEach((item, index) => {
                        item.addEventListener('click', (clickEv) => {
                            clickEv.stopPropagation();
                            openEventDetail(dayEvents[index]);
                            popover.classList.remove('active');
                        });
                    });
                    
                    // Position popover
                    popover.classList.add('active');
                    const rect = dayEl.getBoundingClientRect();
                    const popRect = popover.getBoundingClientRect();
                    
                    // Default position: Above the day cell
                    let top = rect.top + window.scrollY - popRect.height - 10;
                    let left = rect.left + window.scrollX + (rect.width - popRect.width) / 2;
                    
                    // Prevent overflow: if too high, show below the day cell
                    if (top < window.scrollY + 10) {
                        top = rect.bottom + window.scrollY + 10;
                    }
                    // Prevent overflow left/right
                    if (left < 10) left = 10;
                    if (left + popRect.width > window.innerWidth - 10) {
                        left = window.innerWidth - popRect.width - 10;
                    }
                    
                    popover.style.top = `${top}px`;
                    popover.style.left = `${left}px`;
                };
                
                const startHidePopover = () => {
                    hideTimeout = setTimeout(() => {
                        if (popover) popover.classList.remove('active');
                    }, 300);
                };
                
                dayEl.addEventListener('mouseenter', showPopover);
                dayEl.addEventListener('mouseleave', startHidePopover);
                
                // Keep popover open when hovered
                popover.addEventListener('mouseenter', () => clearTimeout(hideTimeout));
                popover.addEventListener('mouseleave', () => {
                    hideTimeout = setTimeout(() => {
                        popover.classList.remove('active');
                    }, 300);
                });
                
                // Toggle for tap/mobile
                dayEl.addEventListener('click', (ev) => {
                    if (ev.target.closest('.cal-event-tag')) return; // let original click work
                    if (popover.classList.contains('active')) {
                        popover.classList.remove('active');
                    } else {
                        showPopover(ev);
                    }
                });
            }
            
            grid.appendChild(dayEl);
        }
    }

    // Init
    loadEvents();
    loadCarousel();
    checkAuth();
    initLeaderboardTicker();
    setupDragScroll();

    // Bridge: allow global functions to update inner scope state
    window._setSearch = (text) => {
        currentSearchText = text;
        renderCards();
    };

    window._renderCards = () => {
        renderCards();
    };

    // ===== REGISTRATION =====
    window.openRegisterConfirm = async (id, title) => {
        if (!currentUser) {
            await checkAuth(); // Try to sync session one last time
        }
        if (!currentUser) {
            toast('กรุณาเข้าสู่ระบบก่อนจองกิจกรรม', 'warning');
            setTimeout(() => window.location.href = '/login', 1500);
            return;
        }
        if (currentUser.role !== 'student') {
            toast('เฉพาะนักศึกษาเท่านั้นที่สามารถจองกิจกรรมได้', 'info');
            return;
        }

        // Check if already registered
        try {
            const resStatus = await fetch(`/api/events/${id}/my-registration`);
            const statusData = await resStatus.json();
            if (statusData && statusData.id) {
                toast('คุณได้จองกิจกรรมนี้ไปแล้ว', 'info');
                return;
            }
        } catch(e) {}

        const regTitleEl = document.getElementById('reg-title');
        const confirmBtn = document.getElementById('reg-confirm-btn');
        const regModal = document.getElementById('reg-confirm-modal');
        if (!regTitleEl || !confirmBtn || !regModal) {
            toast('ไม่สามารถเปิดหน้าจอยืนยันการจองได้', 'error');
            return;
        }
        regTitleEl.textContent = title;
        confirmBtn.onclick = () => registerEvent(id);
        regModal.classList.add('open');
    };

    window.closeRegisterConfirm = () => {
        const regModal = document.getElementById('reg-confirm-modal');
        if (regModal) regModal.classList.remove('open');
    };

    async function registerEvent(id) {
        const btn = document.getElementById('reg-confirm-btn');
        btn.disabled = true;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> กำลังจอง...';

        try {
            const res = await fetch(`/api/events/${id}/register`, { method: 'POST' });
            const data = await res.json();
            if (res.ok) {
                toast('จองกิจกรรมสำเร็จ! ตรวจสอบอีเมลของคุณ', 'success');
                userRegistrations.add(id);
                closeRegisterConfirm();
                if (typeof closeEventDetail === 'function') closeEventDetail();
                loadEvents(); // Reload to update counts
            } else {
                toast(data.message || 'เกิดข้อผิดพลาดในการจอง', 'error');
            }
        } catch (e) {
            toast('ไม่สามารถเชื่อมต่อเซิร์ฟเวอร์ได้', 'error');
        } finally {
            btn.disabled = false;
            btn.textContent = 'ยืนยันการจอง';
        }
    }

    // ===== TOAST NOTIFICATION =====
    

// ===== DRAG-TO-SCROLL for filter bars =====
function setupDragScroll() {
    document.querySelectorAll('.filter-scroll').forEach(el => {
        let isDown = false, startX = 0, scrollLeft = 0;

        const start = (e) => {
            isDown = true;
            el.classList.add('dragging');
            startX = (e.pageX || e.touches[0].pageX) - el.offsetLeft;
            scrollLeft = el.scrollLeft;
        };
        const end = () => {
            isDown = false;
            el.classList.remove('dragging');
        };
        const move = (e) => {
            if (!isDown) return;
            const x = (e.pageX || e.touches[0].pageX) - el.offsetLeft;
            const walk = (x - startX) * 2; // Speed up scroll
            el.scrollLeft = scrollLeft - walk;
        };

        el.addEventListener('mousedown', start);
        el.addEventListener('mouseleave', end);
        el.addEventListener('mouseup', end);
        el.addEventListener('mousemove', (e) => {
            if(isDown) e.preventDefault();
            move(e);
        });

        el.addEventListener('touchstart', start, { passive: true });
        el.addEventListener('touchend', end);
        el.addEventListener('touchmove', move, { passive: true });
    });
}

// ===== VIEW TOGGLE =====
window.setView = (view) => {
    currentView = view;
    const gridBtn = document.getElementById('view-grid');
    const listBtn = document.getElementById('view-list');
    const calBtn = document.getElementById('view-calendar');
    if (gridBtn) gridBtn.classList.toggle('active', view === 'grid');
    if (listBtn) listBtn.classList.toggle('active', view === 'list');
    if (calBtn) calBtn.classList.toggle('active', view === 'calendar');
    
    const container = document.getElementById('cards-container');
    if (container) container.className = 'cards-container' + (view === 'list' ? ' list-view' : '');
    
    if (typeof window._renderCards === 'function') {
        window._renderCards();
    }
}

// ===== SEARCH =====

window.onSearchInput = function(input) {
    const clearBtn = document.getElementById('search-clear');
    if (clearBtn) clearBtn.style.display = input.value ? 'flex' : 'none';

    // Debounce 250ms
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
        // Update currentSearchText inside DOMContentLoaded scope via global bridge
        if (typeof window._setSearch === 'function') window._setSearch(input.value.trim());
    }, 250);
}

window.clearSearch = function() {
    const input = document.getElementById('search-input');
    const clearBtn = document.getElementById('search-clear');
    if (input) input.value = '';
    if (clearBtn) clearBtn.style.display = 'none';
    if (typeof window._setSearch === 'function') window._setSearch('');
    if (input) input.focus();
}


// ===== AUTH =====
// currentUser and userRegistrations are at the top of the file

    async function checkAuth() {
        try {
            const res = await fetch('/api/me');
            if (res.ok) { 
                const d = await res.json(); 
                currentUser = d.user; 
                if (currentUser && currentUser.role === 'student') {
                    await fetchUserRegistrations();
                }
            } else {
                currentUser = null;
                userRegistrations.clear();
            }
        } catch(e) { 
            currentUser = null; 
            userRegistrations.clear();
        }
        initNotifications();
        renderUserControls();
        renderCards();
    }

    async function fetchUserRegistrations() {
        try {
            const res = await fetch('/api/my/registrations');
            if (res.ok) {
                const data = await res.json();
                userRegistrations = new Set(data.filter(r => r.status !== 'cancelled').map(r => r.event_id));
            }
        } catch(e) {}
    }

function renderUserControls() {
    const controls = document.getElementById('user-controls');
    if (!controls) return;

    if (currentUser) {
        const roleColor = { admin: '#ef4444', major: '#f59e0b', student: '#10b981' }[currentUser.role] || '#94a3b8';
        const profileLink = currentUser.role === 'student'
            ? `<a href="/profile" class="nav-btn nav-btn-outline"><i class="fa-solid fa-user"></i><span>โปรไฟล์</span></a>` : '';
        controls.innerHTML = `
            ${profileLink}
            <div class="nav-btn nav-btn-ghost" style="gap:6px;cursor:default;">
                <i class="fa-solid fa-circle" style="color:${roleColor};font-size:8px;"></i>
                <span style="max-width:100px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${currentUser.name}</span>
            </div>
            <button class="nav-btn nav-btn-outline" onclick="doLogout()" style="color:#dc2626;">
                <i class="fa-solid fa-right-from-bracket"></i>
            </button>`;
    } else {
        controls.innerHTML = `
            <a href="/login" class="nav-btn nav-btn-blue">
                <i class="fa-solid fa-right-to-bracket"></i>
                <span>เข้าสู่ระบบ</span>
            </a>`;
    }
}

// ===== SHARE =====
let qrCodeInstance = null;

window.shareWebsite = function() {
    const modal = document.getElementById('share-modal');
    const input = document.getElementById('share-url-input');
    const openBtn = document.getElementById('open-new-tab');
    const currentUrl = window.location.origin;

    modal.classList.add('open');
    input.value = currentUrl;
    openBtn.href = currentUrl;

    // Generate QR Code
    const qrContainer = document.getElementById('qrcode');
    qrContainer.innerHTML = ''; // Clear old one
    new QRCode(qrContainer, {
        text: currentUrl,
        width: 180,
        height: 180,
        colorDark: "#1e293b",
        colorLight: "#ffffff",
        correctLevel: QRCode.CorrectLevel.H
    });
}

window.closeShareModal = function() {
    document.getElementById('share-modal').classList.remove('open');
}

function handleShareOverlayClick(e) {
    if (e.target === e.currentTarget) closeShareModal();
}

window.copyShareLink = async function() {
    const input = document.getElementById('share-url-input');
    try {
        await navigator.clipboard.writeText(input.value);
        showShareToast();
    } catch(e) {
        input.select();
        document.execCommand('copy');
        showShareToast();
    }
}

function showShareToast() {
    const t = document.createElement('div');
    t.style.cssText = 'position:fixed;bottom:24px;left:50%;transform:translateX(-50%);background:#1e293b;color:white;padding:10px 22px;border-radius:12px;font-size:14px;font-family:Kanit,sans-serif;z-index:9999;box-shadow:0 8px 24px rgba(0,0,0,0.25);animation:slideUp 0.3s ease;';
    t.innerHTML = '<i class="fa-solid fa-check" style="color:#4ade80;margin-right:6px;"></i>คัดลอกลิงก์แล้ว!';
    document.body.appendChild(t);
    setTimeout(() => t.remove(), 2500);
}

window.doLogout = async function() {
    await fetch('/api/logout', { method: 'POST' });
    window.location.reload();
}

// ===== LEADERBOARD =====
window.openPublicLeaderboard = async function() {
    const modal = document.getElementById('public-leaderboard-modal');
    modal.classList.add('open');
    const container = document.getElementById('public-leaderboard-list');
    container.innerHTML = '<div class="lb-loading"><div class="loading-spinner"></div><p>กำลังโหลด...</p></div>';

    try {
        const res = await fetch('/api/leaderboard');
        const data = await res.json();
        container.innerHTML = '';

        if (!data.length) {
            container.innerHTML = '<div class="lb-loading"><i class="fa-solid fa-inbox" style="font-size:32px;opacity:0.3;"></i><p>ยังไม่มีข้อมูลคะแนน</p></div>';
            return;
        }

        data.forEach((s, i) => {
            const rankNum = i + 1;
            const rankClass = rankNum <= 3 ? `r${rankNum}` : 'rn';
            const itemClass = rankNum <= 3 ? `lb-item rank-${rankNum}` : 'lb-item';
            const icon = rankNum === 1 ? '🥇' : rankNum === 2 ? '🥈' : rankNum === 3 ? '🥉' : rankNum;
            container.innerHTML += `
                <div class="${itemClass}">
                    <div class="lb-rank ${rankClass}">${icon}</div>
                    <div class="lb-info">
                        <div class="lb-name">${s.name || s.username}</div>
                        <div class="lb-major">${s.major || '-'}</div>
                    </div>
                    <div class="lb-score">${s.score}<span>คะแนน</span></div>
                </div>`;
        });
    } catch(e) { console.error(e); }
}

window.closePublicLeaderboard = function() {
    document.getElementById('public-leaderboard-modal').classList.remove('open');
}

function handleLbOverlayClick(e) {
    if (e.target === e.currentTarget) closePublicLeaderboard();
}

// Close on ESC
document.addEventListener('keydown', e => { 
    if (e.key === 'Escape') {
        closePublicLeaderboard();
        closeShareModal();
    }
});

// ===== TICKER =====
let tickerData = [], tickerIndex = 0;

async function initLeaderboardTicker() {
    const tickerEl = document.getElementById('leaderboard-ticker');
    const contentEl = document.getElementById('ticker-content');
    if (!tickerEl || !contentEl) return;
    try {
        const res = await fetch('/api/leaderboard');
        tickerData = await res.json();
        if (tickerData.length > 0) {
            tickerEl.style.display = 'flex';
            updateTicker();
            setInterval(updateTicker, 4000);
        }
    } catch(e) {}
}

function updateTicker() {
    const contentEl = document.getElementById('ticker-content');
    if (!contentEl || !tickerData.length) return;
    const s = tickerData[tickerIndex];
    const rank = tickerIndex + 1;
    const medals = ['🥇','🥈','🥉'];
    const icon = rank <= 3 ? medals[rank-1] : `#${rank}`;

    contentEl.style.opacity = '0';
    setTimeout(() => {
        contentEl.innerHTML = `<span style="color:#fde047;font-weight:700;">${icon} อันดับ ${rank}</span> &nbsp;<span style="color:rgba(255,255,255,0.9);font-weight:600;">${s.name}</span> &nbsp;<span style="background:rgba(250,204,21,0.2);color:#fde047;padding:2px 8px;border-radius:10px;font-size:12px;font-weight:700;">${s.score} คะแนน</span>`;
        contentEl.style.opacity = '1';
        tickerIndex = (tickerIndex + 1) % Math.min(tickerData.length, 10);
    }, 350);
}

// ===== NOTIFICATIONS =====
async function initNotifications() {
    const containers = document.querySelectorAll('.notification-container');
    containers.forEach(c => {
        c.style.setProperty('display', 'none', 'important');
    });
    // Disabled as notifications system is removed
}

async function updateUnreadCount() {
    try {
        const res = await fetch('/api/notifications/unread-count');
        if (!res.ok) return;
        const data = await res.json();
        if (typeof data.count !== 'number') return;
        // Update all badges (Desktop and Mobile)
        const badges = document.querySelectorAll('.notif-badge');
        badges.forEach(badge => {
            if (data.count > 0) {
                badge.textContent = data.count;
                badge.style.display = 'flex';
            } else {
                badge.style.display = 'none';
            }
        });
    } catch(e) {console.error('Unread count error:', e);}
}

window.toggleNotifications = async function(event) {
    if (event) event.stopPropagation();
    const isMobile = window.innerWidth <= 768;
    const desktopDropdown = document.querySelector('.desktop-only .notif-dropdown');
    const mobileDropdown = document.getElementById('notif-dropdown-mobile');
    const backdrop = document.getElementById('notif-backdrop');
    
    let isActive = false;
    if (isMobile && mobileDropdown) {
        isActive = mobileDropdown.classList.toggle('active');
        if (desktopDropdown) desktopDropdown.classList.remove('active');
    } else if (desktopDropdown) {
        isActive = desktopDropdown.classList.toggle('active');
        if (mobileDropdown) mobileDropdown.classList.remove('active');
    }
    
    if (backdrop) backdrop.classList.toggle('active', isActive);
    
    if (window.innerWidth <= 768) {
        document.body.style.overflow = isActive ? 'hidden' : '';
    }
    
    if (isActive) {
        renderNotifications();
        if (window.innerWidth > 768) {
            const closeOnClickOutside = (e) => {
                if (!e.target.closest('.notification-container')) {
                    closeNotifications();
                    document.removeEventListener('click', closeOnClickOutside);
                }
            };
            setTimeout(() => document.addEventListener('click', closeOnClickOutside), 10);
        }
    }
};

window.closeNotifications = function(event) {
    if (event) event.stopPropagation();
    document.querySelectorAll('.notif-dropdown').forEach(d => d.classList.remove('active'));
    const backdrop = document.getElementById('notif-backdrop');
    if (backdrop) backdrop.classList.remove('active');
    document.body.style.overflow = '';
};

async function renderNotifications() {
    const lists = document.querySelectorAll('.notif-list');
    if (lists.length === 0) return;
    
    lists.forEach(l => l.innerHTML = '<div class="notif-empty"><i class="fa-solid fa-spinner fa-spin"></i> กำลังโหลด...</div>');
    
    try {
        const res = await fetch('/api/notifications');
        if (!res.ok) {
            lists.forEach(l => l.innerHTML = '<div class="notif-empty"><i class="fa-solid fa-triangle-exclamation" style="color:#f59e0b;"></i> ไม่สามารถโหลดข้อมูลได้</div>');
            return;
        }
        const notifs = await res.json();
        if (!Array.isArray(notifs)) throw new Error('Invalid response');
        
        lists.forEach(list => {
            if (!Array.isArray(notifs) || notifs.length === 0) {
                list.innerHTML = '<div class="notif-empty"><i class="fa-regular fa-bell-slash" style="font-size:24px;opacity:0.3;display:block;margin-bottom:8px;"></i>ไม่มีการแจ้งเตือน</div>';
                return;
            }
            
            list.innerHTML = '';
            notifs.forEach(n => {
                const item = document.createElement('div');
                item.className = `notif-item ${n.is_read ? '' : 'unread'} ${n.type || ''}`;
                if (n.id) item.onclick = () => markAsRead(n.id, item);
                
let time = 'เมื่อสักครู่';
            try {
                time = new Date(n.created_at).toLocaleString('th-TH', { 
                    day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' 
                });
            } catch(e) {}
                
                const typeIcon = {
                    'success': '<i class="fa-solid fa-circle-check" style="color:#10b981;"></i>',
                    'danger':  '<i class="fa-solid fa-circle-xmark" style="color:#ef4444;"></i>',
                    'warning': '<i class="fa-solid fa-triangle-exclamation" style="color:#f59e0b;"></i>',
                    'info':    '<i class="fa-solid fa-circle-info" style="color:#0284c7;"></i>'
                }[n.type] || '<i class="fa-solid fa-bell" style="color:#94a3b8;"></i>';
                
                item.innerHTML = `
                    <div style="display:flex;align-items:flex-start;gap:10px;">
                        <div style="flex-shrink:0;margin-top:1px;">${typeIcon}</div>
                        <div style="flex:1;min-width:0;">
                            <div class="notif-item-title">${h(n.title)}</div>
                            <div class="notif-item-message">${h(n.message)}</div>
                            <div class="notif-item-time"><i class="fa-regular fa-clock"></i> ${time}</div>
                        </div>
                        ${!n.is_read ? '<div style="width:8px;height:8px;background:#0284c7;border-radius:50%;flex-shrink:0;margin-top:4px;"></div>' : ''}
                    </div>
                `;
                list.appendChild(item);
            });
        });
    } catch(e) {
        lists.forEach(l => l.innerHTML = '<div class="notif-empty"><i class="fa-solid fa-triangle-exclamation" style="color:#f59e0b;"></i> ไม่สามารถโหลดข้อมูลได้</div>');
    }
}

async function markAsRead(id, element) {
    closeNotifications();
    try {
        const res = await fetch('/api/notifications/mark-as-read', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id })
        });
        if (res.ok) {
            if (element) {
                element.classList.remove('unread');
                element.style.borderLeft = '';
            }
            updateUnreadCount();
        }
    } catch(e) { console.error(e); }
}

window.markAllAsRead = async function() {
    try {
        await fetch('/api/notifications/mark-as-read', { method: 'POST' });
        document.querySelectorAll('.notif-item.unread').forEach(el => {
            el.classList.remove('unread');
            el.style.borderLeft = '';
        });
        // Update all badges (Desktop and Mobile)
        document.querySelectorAll('.notif-badge').forEach(badge => {
            badge.style.display = 'none';
        });
        updateUnreadCount();
    } catch(e) { console.error(e); }
}

(function setupSwipeClose() {
    let startY = 0, isDragging = false;
    document.addEventListener('touchstart', (e) => {
        const dropdown = document.getElementById('notif-dropdown-mobile');
        if (dropdown && dropdown.classList.contains('active') && dropdown.contains(e.target)) {
            startY = e.touches[0].clientY;
            isDragging = true;
        }
    }, { passive: true });
    document.addEventListener('touchmove', (e) => {
        if (!isDragging) return;
        const dropdown = document.getElementById('notif-dropdown-mobile');
        if (!dropdown) return;
        const dy = e.touches[0].clientY - startY;
        if (dy > 0) {
            dropdown.style.transform = `translateY(${dy}px)`;
            dropdown.style.transition = 'none';
        }
    }, { passive: true });
    document.addEventListener('touchend', (e) => {
        if (!isDragging) return;
        isDragging = false;
        const dropdown = document.getElementById('notif-dropdown-mobile');
        if (!dropdown) return;
        const dy = e.changedTouches[0].clientY - startY;
        dropdown.style.transition = '';
        dropdown.style.transform = '';
        if (dy > 80) closeNotifications();
    });
})();

window.openEventDetail = function(evt) {
    const modal = document.getElementById('activity-detail-modal');
    if (!modal) return;
    
    document.getElementById('detail-title').textContent = evt.title.replace(/\*$/, '');
    document.getElementById('detail-date').textContent = evt.originalDate || '-';
    document.getElementById('detail-location').textContent = evt.location || 'คณะวิทยาศาสตร์และเทคโนโลยี';
    document.getElementById('detail-owner').textContent = evt.owner || 'สโมสรนักศึกษา';
    document.getElementById('detail-description').textContent = evt.description || 'ไม่มีข้อมูลรายละเอียดเพิ่มเติมสำหรับกิจกรรมนี้';
    document.getElementById('detail-score').textContent = evt.score || '0';
    
    const catEl = document.getElementById('detail-category');
    if (evt.category === 'กิจกรรมมหาวิทยาลัย') {
        catEl.textContent = 'มหาวิทยาลัย';
        catEl.className = 'category-badge cat-uni';
    } else if (evt.owner && (evt.owner.includes('สาขาวิชา') || evt.owner.includes('คณะ'))) {
        catEl.textContent = 'คณะ/สาขา';
        catEl.className = 'category-badge cat-major';
    } else {
        catEl.textContent = 'ชมรม/ทั่วไป';
        catEl.className = 'category-badge cat-club';
    }

    const partEl = document.getElementById('detail-participants');
    partEl.textContent = evt.max_participants > 0 ? `${evt.registered_count}/${evt.max_participants}` : 'ไม่จำกัด';

    const actionsEl = document.getElementById('detail-actions');
    const isRegistered = userRegistrations.has(evt.id);
    const isFull = evt.max_participants > 0 && evt.registered_count >= evt.max_participants;
    
    const now = new Date();
    const isToday = evt.start.day === now.getDate() && evt.start.month === now.getMonth() && evt.start.year === (now.getFullYear() + 543);

    if (evt.registration_open || (isToday && evt.status !== 'เสร็จสิ้น')) {
        let btnText = 'จองกิจกรรมนี้';
        let btnClass = 'btn nav-btn-blue';
        if (isRegistered) {
            btnText = '<i class="fa-solid fa-check-circle"></i> จองแล้ว';
            btnClass = 'btn registered';
        } else if (isFull) {
            btnText = 'จองที่นั่งสำรอง';
            btnClass = 'btn nav-btn-amber';
        }
        actionsEl.innerHTML = `<button class="${btnClass}" onclick="openRegisterConfirm('${j(evt.id)}', '${j(evt.title)}')">${btnText}</button>`;
    } else {
        actionsEl.innerHTML = `<button class="btn" style="background:#f1f5f9;color:#94a3b8;cursor:not-allowed;" disabled>ปิดรับสมัครแล้ว</button>`;
    }
    
    modal.classList.add('open');
    document.body.style.overflow = 'hidden';
}

window.closeActivityDetail = function() {
    const modal = document.getElementById('activity-detail-modal');
    if (modal) modal.classList.remove('open');
    document.body.style.overflow = '';
}

document.addEventListener('keydown', e => {
    if (e.key === 'Escape') {
        if (typeof closePublicLeaderboard === 'function') closePublicLeaderboard();
        if (typeof closeShareModal === 'function') closeShareModal();
        closeActivityDetail();
        closeNotifications();
    }
});
});
