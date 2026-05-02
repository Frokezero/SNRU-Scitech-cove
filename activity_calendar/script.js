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
        const width = container.offsetWidth;
        
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
            const width = container.offsetWidth;
            
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
    let currentYear = 2569;
    let parsedEventsList = [];

    // Elements
    const branchFiltersContainer = document.getElementById('branch-filters');

    // Parse events into structured cards
    async function loadEvents() {
        try {
            const response = await fetch('/api/events');
            const eventsData = await response.json();
            
            parsedEventsList = [];
            eventsData.forEach(event => {
                const dateStr = event.date;
                if (!dateStr || dateStr.trim() === '') return;
                
                let isRange = dateStr.includes('-');
                let parts = isRange ? dateStr.split('-') : [dateStr];
                
                const extractDate = (str) => {
                    let day = null, month = null, year = null;
                    let dayMatch = str.match(/\b(\d{1,2})\b/);
                    if (dayMatch && parseInt(dayMatch[1]) <= 31) day = parseInt(dayMatch[1]);
                    
                    let yearMatch = str.match(/\b(68|69|70)\b/);
                    if (yearMatch) year = parseInt(yearMatch[1]) + 2500;
                    
                    for (let i = 0; i < thaiMonthsAbbr.length; i++) {
                        if (str.includes(thaiMonthsAbbr[i]) || str.includes(thaiMonthsFull[i])) {
                            month = i;
                            break;
                        }
                    }
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
            btn.textContent = `${thaiMonthsFull[ym.month]} ${ym.year % 100}`;
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
                btns.forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
                currentBranchFilter = e.target.getAttribute('data-branch');
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
            displayEvents = displayEvents.filter(e => e.owner === currentBranchFilter);
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
            let startYear = evt.start.year ? (evt.start.year % 100) : 69;
            let endYear = evt.end && evt.end.year ? (evt.end.year % 100) : startYear;

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

            card.innerHTML = `
                <div class="card-date-box ${colorClass}">
                    ${dateBoxHtml}
                </div>
                <div class="card-content">
                    <div class="card-body">
                        ${cleanTitle}
                    </div>
                    <div class="card-footer">
                        <div>สถานะ: ${evt.status}</div>
                        <div class="card-owner">สังกัด: ${evt.owner}</div>
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
});
