/**
 * University Activity Calendar - Shared UI Utilities
 * Standardized components for Toast, Loading, and Global Interactions
 */

// 1. Toast Notification System
window.toast = function(msg, type = 'success') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.style.cssText = `
            position: fixed; bottom: 20px; right: 20px; z-index: 9999;
            display: flex; flex-direction: column; gap: 10px; pointer-events: none;
        `;
        document.body.appendChild(container);
    }

    const div = document.createElement('div');
    div.style.cssText = `
        padding: 14px 22px; border-radius: 12px; background: white; color: #1e293b;
        box-shadow: 0 10px 25px rgba(0,0,0,0.1);
        display: flex; align-items: center; gap: 12px; font-size: 14px; font-weight: 600;
        border-left: 5px solid #10b981; min-width: 300px; transform: translateX(130%);
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        pointer-events: auto;
    `;

    // Dark mode support
    if (document.documentElement.classList.contains('dark-theme')) {
        div.style.background = '#1e293b';
        div.style.color = '#f8fafc';
        div.style.boxShadow = '0 10px 25px rgba(0,0,0,0.4)';
    }

    let icon = '<i class="fa-solid fa-circle-check" style="color:#10b981;"></i>';
    if (type === 'error') {
        div.style.borderLeftColor = '#ef4444';
        icon = '<i class="fa-solid fa-circle-xmark" style="color:#ef4444;"></i>';
    } else if (type === 'warning') {
        div.style.borderLeftColor = '#f59e0b';
        icon = '<i class="fa-solid fa-triangle-exclamation" style="color:#f59e0b;"></i>';
    } else if (type === 'info') {
        div.style.borderLeftColor = '#0284c7';
        icon = '<i class="fa-solid fa-circle-info" style="color:#0284c7;"></i>';
    }

    div.innerHTML = `${icon} <span style="flex:1;">${msg}</span>`;
    container.appendChild(div);
    
    // Animate In
    setTimeout(() => div.style.transform = 'translateX(0)', 10);
    
    // Auto Remove
    const remove = () => {
        div.style.transform = 'translateX(130%)';
        div.style.opacity = '0';
        setTimeout(() => div.remove(), 400);
    };
    
    setTimeout(remove, 4500);
    div.onclick = remove;
};

// 2. Loading Overlay System
window.showLoading = function(show = true) {
    let overlay = document.getElementById('global-loading');
    if (!overlay && show) {
        overlay = document.createElement('div');
        overlay.id = 'global-loading';
        overlay.style.cssText = `
            position: fixed; inset: 0; background: rgba(0,0,0,0.5);
            backdrop-filter: blur(4px); z-index: 10000;
            display: flex; flex-direction: column; align-items: center; justify-content: center;
            color: white; font-family: 'Kanit', sans-serif; opacity: 0; transition: opacity 0.3s;
        `;
        overlay.innerHTML = `
            <div style="background:rgba(30,41,59,0.8); padding:30px; border-radius:20px; text-align:center; box-shadow:0 20px 50px rgba(0,0,0,0.3); border:1px solid rgba(255,255,255,0.1);">
                <i class="fa-solid fa-spinner fa-spin" style="font-size:40px; color:#facc15; margin-bottom:15px;"></i>
                <div style="font-weight:600; font-size:18px;">กำลังดำเนินการ...</div>
                <div style="font-size:13px; opacity:0.7; margin-top:5px;">โปรดรอสักครู่</div>
            </div>
        `;
        document.body.appendChild(overlay);
        setTimeout(() => overlay.style.opacity = '1', 10);
    } else if (overlay && !show) {
        overlay.style.opacity = '0';
        setTimeout(() => overlay.remove(), 300);
    }
};

// 3. Scroll to Top Utility
(function setupScrollToTop() {
    const btn = document.createElement('button');
    btn.id = 'btn-back-to-top';
    btn.innerHTML = '<i class="fa-solid fa-arrow-up"></i>';
    btn.style.cssText = `
        position: fixed; bottom: 85px; right: 25px; width: 45px; height: 45px;
        border-radius: 50%; background: #0284c7; color: white; border: none;
        box-shadow: 0 4px 15px rgba(2,132,199,0.4); cursor: pointer;
        display: none; align-items: center; justify-content: center; z-index: 998;
        transition: all 0.3s;
    `;
    document.body.appendChild(btn);

    window.onscroll = () => {
        if (document.body.scrollTop > 300 || document.documentElement.scrollTop > 300) {
            btn.style.display = 'flex';
        } else {
            btn.style.display = 'none';
        }
    };

    btn.onclick = () => window.scrollTo({ top: 0, behavior: 'smooth' });
})();
