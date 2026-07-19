(function() {
    const lucideToFA = {
        'activity': 'fa-solid fa-pulse',
        'alert-circle': 'fa-solid fa-circle-exclamation',
        'alert-triangle': 'fa-solid fa-triangle-exclamation',
        'arrow-left': 'fa-solid fa-arrow-left',
        'arrow-right': 'fa-solid fa-arrow-right',
        'archive': 'fa-solid fa-box-archive',
        'bar-chart-2': 'fa-solid fa-chart-simple',
        'bar-chart-3': 'fa-solid fa-chart-column',
        'bell': 'fa-solid fa-bell',
        'building': 'fa-solid fa-building',
        'building-2': 'fa-solid fa-city',
        'calendar': 'fa-solid fa-calendar-days',
        'calendar-days': 'fa-solid fa-calendar-days',
        'check': 'fa-solid fa-check',
        'check-circle': 'fa-solid fa-circle-check',
        'check-circle-2': 'fa-solid fa-circle-check',
        'chevron-left': 'fa-solid fa-chevron-left',
        'chevron-right': 'fa-solid fa-chevron-right',
        'chevrons-left': 'fa-solid fa-angles-left',
        'chevrons-right': 'fa-solid fa-angles-right',
        'clipboard-check': 'fa-solid fa-clipboard-check',
        'clipboard-list': 'fa-solid fa-clipboard-list',
        'clock': 'fa-solid fa-clock',
        'contact': 'fa-solid fa-address-book',
        'database': 'fa-solid fa-database',
        'download': 'fa-solid fa-file-arrow-down',
        'file-down': 'fa-solid fa-file-arrow-down',
        'edit': 'fa-solid fa-pen-to-square',
        'edit-2': 'fa-solid fa-pen-to-square',
        'edit-3': 'fa-solid fa-pen',
        'home': 'fa-solid fa-house-chimney',
        'inbox': 'fa-solid fa-inbox',
        'info': 'fa-solid fa-circle-info',
        'layers': 'fa-solid fa-layer-group',
        'eye': 'fa-solid fa-eye',
        'eye-off': 'fa-solid fa-eye-slash',
        'file': 'fa-solid fa-file',
        'file-bar-chart': 'fa-solid fa-file-chart-column',
        'file-check': 'fa-solid fa-file-circle-check',
        'file-plus': 'fa-solid fa-file-circle-plus',
        'file-spreadsheet': 'fa-solid fa-file-excel',
        'file-symlink': 'fa-solid fa-file-import',
        'file-text': 'fa-solid fa-file-lines',
        'file-up': 'fa-solid fa-file-arrow-up',
        'files': 'fa-solid fa-files',
        'filter': 'fa-solid fa-filter',
        'folder': 'fa-solid fa-folder',
        'folder-open': 'fa-solid fa-folder-open',
        'folder-plus': 'fa-solid fa-folder-plus',
        'folder-search': 'fa-solid fa-folder-tree',
        'folder-tree': 'fa-solid fa-folder-tree',
        'git-branch': 'fa-solid fa-code-branch',
        'hard-drive': 'fa-solid fa-hard-drive',
        'hard-hat': 'fa-solid fa-helmet-safety',
        'history': 'fa-solid fa-history',
        'key': 'fa-solid fa-key',
        'key-round': 'fa-solid fa-key',
        'landmark': 'fa-solid fa-landmark',
        'layout-dashboard': 'fa-solid fa-chart-line',
        'list-checks': 'fa-solid fa-list-check',
        'lock': 'fa-solid fa-lock',
        'log-in': 'fa-solid fa-right-to-bracket',
        'log-out': 'fa-solid fa-right-from-bracket',
        'mail': 'fa-solid fa-envelope',
        'mail-open': 'fa-solid fa-envelope-open',
        'map': 'fa-solid fa-map',
        'map-pin': 'fa-solid fa-map-pin',
        'menu': 'fa-solid fa-bars',
        'more-horizontal': 'fa-solid fa-ellipsis',
        'more-vertical': 'fa-solid fa-ellipsis-vertical',
        'pencil': 'fa-solid fa-pencil',
        'phone': 'fa-solid fa-phone',
        'plus': 'fa-solid fa-plus',
        'plus-circle': 'fa-solid fa-circle-plus',
        'printer': 'fa-solid fa-print',
        'refresh-cw': 'fa-solid fa-arrows-rotate',
        'rotate-ccw': 'fa-solid fa-rotate-left',
        'save': 'fa-solid fa-floppy-disk',
        'search': 'fa-solid fa-magnifying-glass',
        'send': 'fa-solid fa-paper-plane',
        'settings': 'fa-solid fa-gear',
        'sun': 'fa-solid fa-sun',
        'moon': 'fa-solid fa-moon',
        'shield': 'fa-solid fa-shield-halved',
        'shield-alert': 'fa-solid fa-shield-halved',
        'shield-check': 'fa-solid fa-shield-halved',
        'sliders-horizontal': 'fa-solid fa-sliders',
        'trash': 'fa-solid fa-trash-can',
        'trash-2': 'fa-solid fa-trash-can',
        'trending-up': 'fa-solid fa-arrow-trend-up',
        'upload-cloud': 'fa-solid fa-cloud-arrow-up',
        'user': 'fa-solid fa-user',
        'user-check': 'fa-solid fa-user-check',
        'user-cog': 'fa-solid fa-user-gear',
        'user-plus': 'fa-solid fa-user-plus',
        'user-x': 'fa-solid fa-user-xmark',
        'users': 'fa-solid fa-users',
        'wallet': 'fa-solid fa-wallet',
        'x': 'fa-solid fa-xmark',
        'x-circle': 'fa-solid fa-circle-xmark',
        'loader': 'fa-solid fa-spinner fa-spin',
        'loader-2': 'fa-solid fa-spinner fa-spin',
        
        // Database dynamic icons mapping
        'zap': 'fa-solid fa-bolt',
        'check-square': 'fa-solid fa-square-check',
        'fence': 'fa-solid fa-grip-lines-vertical',
        'milestone': 'fa-solid fa-signs-post',
        'droplets': 'fa-solid fa-droplet',
        'git-commit': 'fa-solid fa-circle-dot'
    };

    function replaceIcons() {
        const els = document.querySelectorAll('[data-lucide]');
        els.forEach(el => {
            const iconName = el.getAttribute('data-lucide');
            const faClass = lucideToFA[iconName] || 'fa-solid fa-circle-question';
            
            let newEl;
            if (el.tagName === 'SVG') {
                newEl = document.createElement('i');
                el.classList.forEach(cls => {
                    if (cls !== 'lucide' && !cls.startsWith('lucide-')) {
                        newEl.classList.add(cls);
                    }
                });
                if (el.getAttribute('style')) {
                    newEl.setAttribute('style', el.getAttribute('style'));
                }
                newEl.setAttribute('data-lucide', iconName);
            } else {
                newEl = el;
                newEl.className = Array.from(newEl.classList)
                    .filter(c => !c.startsWith('lucide') && !c.startsWith('fa-'))
                    .join(' ');
            }

            faClass.split(' ').forEach(c => newEl.classList.add(c));

            const styleAttr = newEl.getAttribute('style') || '';
            let widthMatch = styleAttr.match(/width:\s*(\d+)px/);
            if (widthMatch) {
                const pxVal = widthMatch[1];
                newEl.style.fontSize = pxVal + 'px';
                if (!styleAttr.match(/display:\s*none/)) {
                    newEl.style.display = 'inline-flex';
                } else {
                    newEl.style.display = 'none';
                }
                newEl.style.alignItems = 'center';
                newEl.style.justifyContent = 'center';
                newEl.style.lineHeight = '1';
            }

            if (el !== newEl) {
                el.parentNode.replaceChild(newEl, el);
            }
        });
    }

    window.lucide = {
        createIcons: function() {
            replaceIcons();
        }
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', replaceIcons);
    } else {
        replaceIcons();
    }
})();
