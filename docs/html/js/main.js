/**
 * OpenCitiVibes Documentation Site
 * Interactive JavaScript
 */

(function() {
    'use strict';

    // ============================================
    // Mobile Menu Toggle
    // ============================================
    const mobileMenuBtn = document.querySelector('.mobile-menu-btn');
    const navLinks = document.querySelector('.nav-links');

    if (mobileMenuBtn && navLinks) {
        mobileMenuBtn.addEventListener('click', () => {
            navLinks.classList.toggle('active');
            mobileMenuBtn.classList.toggle('active');
        });

        // Close mobile menu when a link is clicked
        navLinks.querySelectorAll('a').forEach(link => {
            link.addEventListener('click', () => {
                navLinks.classList.remove('active');
                mobileMenuBtn.classList.remove('active');
            });
        });
    }

    // ============================================
    // Screenshot Tabs
    // ============================================
    const tabBtns = document.querySelectorAll('.tab-btn');
    const screenshotDisplay = document.getElementById('screenshot-display');

    const screenshots = {
        home: {
            title: 'Homepage',
            description: 'Main landing page with category cards and featured ideas',
            image: 'images/screenshot-home.png'
        },
        idea: {
            title: 'Idea View',
            description: 'Detailed idea page with voting, comments, and quality ratings',
            image: 'images/screenshot-idea.png'
        },
        submit: {
            title: 'Explorer',
            description: 'Browse and search through all submitted ideas',
            image: 'images/screenshot-submit.png'
        },
        admin: {
            title: 'Admin Panel',
            description: 'Moderation dashboard for reviewing pending content',
            image: 'images/screenshot-admin.png'
        }
    };

    // Initialize with home screenshot on page load
    function updateScreenshot(tab) {
        const screenshot = screenshots[tab];
        if (screenshotDisplay && screenshot) {
            screenshotDisplay.innerHTML = `
                <img src="${screenshot.image}"
                     alt="${screenshot.title}"
                     class="screenshot-image"
                     onerror="this.parentElement.innerHTML='<div class=\\'placeholder-content\\'><svg viewBox=\\'0 0 24 24\\' fill=\\'none\\' stroke=\\'currentColor\\' stroke-width=\\'1.5\\'><rect x=\\'3\\' y=\\'3\\' width=\\'18\\' height=\\'18\\' rx=\\'2\\'/><circle cx=\\'8.5\\' cy=\\'8.5\\' r=\\'1.5\\'/><path d=\\'M21 15l-5-5L5 21\\'/></svg><p>${screenshot.title}</p><span>Screenshot not found. Add ${screenshot.image}</span></div>'"
                />
            `;
        }
    }

    // Show home screenshot by default
    if (screenshotDisplay) {
        updateScreenshot('home');
    }

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            // Remove active from all buttons
            tabBtns.forEach(b => b.classList.remove('active'));
            // Add active to clicked button
            btn.classList.add('active');

            // Update screenshot display
            const tab = btn.dataset.tab;
            updateScreenshot(tab);
        });
    });

    // ============================================
    // Smooth Scroll for Anchor Links
    // ============================================
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            const targetId = this.getAttribute('href');
            if (targetId === '#') return;

            const target = document.querySelector(targetId);
            if (target) {
                e.preventDefault();
                const navHeight = document.querySelector('.navbar')?.offsetHeight || 80;
                const targetPosition = target.getBoundingClientRect().top + window.pageYOffset - navHeight - 20;

                window.scrollTo({
                    top: targetPosition,
                    behavior: 'smooth'
                });

                // Update URL without jumping
                history.pushState(null, null, targetId);
            }
        });
    });

    // ============================================
    // Sidebar Active Link (Documentation Pages)
    // ============================================
    const docsSidebar = document.querySelector('.docs-sidebar');
    if (docsSidebar) {
        const sidebarLinks = docsSidebar.querySelectorAll('a');
        const sections = document.querySelectorAll('h2[id], h3[id]');

        function updateActiveLink() {
            const scrollPosition = window.scrollY + 100;

            let currentSection = '';
            sections.forEach(section => {
                if (section.offsetTop <= scrollPosition) {
                    currentSection = section.id;
                }
            });

            sidebarLinks.forEach(link => {
                link.classList.remove('active');
                if (link.getAttribute('href') === `#${currentSection}`) {
                    link.classList.add('active');
                }
            });
        }

        window.addEventListener('scroll', updateActiveLink);
        updateActiveLink();
    }

    // ============================================
    // Navbar Background on Scroll
    // ============================================
    const navbar = document.querySelector('.navbar');
    if (navbar) {
        function updateNavbar() {
            if (window.scrollY > 50) {
                navbar.style.boxShadow = '0 1px 3px rgba(0, 0, 0, 0.1)';
            } else {
                navbar.style.boxShadow = 'none';
            }
        }

        window.addEventListener('scroll', updateNavbar);
        updateNavbar();
    }

    // ============================================
    // Copy Code Blocks
    // ============================================
    document.querySelectorAll('pre code').forEach(block => {
        // Create copy button
        const copyBtn = document.createElement('button');
        copyBtn.className = 'copy-btn';
        copyBtn.innerHTML = `
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
                <path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/>
            </svg>
        `;
        copyBtn.title = 'Copy to clipboard';

        // Style the button
        copyBtn.style.cssText = `
            position: absolute;
            top: 8px;
            right: 8px;
            padding: 6px;
            background: rgba(255, 255, 255, 0.1);
            border: none;
            border-radius: 4px;
            cursor: pointer;
            opacity: 0;
            transition: opacity 0.2s;
        `;
        copyBtn.querySelector('svg').style.cssText = `
            width: 16px;
            height: 16px;
            color: #9ca3af;
        `;

        // Position the pre element
        const pre = block.parentElement;
        pre.style.position = 'relative';
        pre.appendChild(copyBtn);

        // Show/hide on hover
        pre.addEventListener('mouseenter', () => {
            copyBtn.style.opacity = '1';
        });
        pre.addEventListener('mouseleave', () => {
            copyBtn.style.opacity = '0';
        });

        // Copy functionality
        copyBtn.addEventListener('click', async () => {
            try {
                await navigator.clipboard.writeText(block.textContent);
                copyBtn.innerHTML = `
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="20 6 9 17 4 12"/>
                    </svg>
                `;
                copyBtn.querySelector('svg').style.cssText = `
                    width: 16px;
                    height: 16px;
                    color: #10b981;
                `;
                setTimeout(() => {
                    copyBtn.innerHTML = `
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
                            <path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/>
                        </svg>
                    `;
                    copyBtn.querySelector('svg').style.cssText = `
                        width: 16px;
                        height: 16px;
                        color: #9ca3af;
                    `;
                }, 2000);
            } catch (err) {
                console.error('Failed to copy:', err);
            }
        });
    });

    // ============================================
    // Animate Elements on Scroll
    // ============================================
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    // Observe feature cards, tech cards, and instance cards
    document.querySelectorAll('.feature-card, .tech-card, .instance-card').forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(20px)';
        el.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
        observer.observe(el);
    });

    // ============================================
    // Console Easter Egg
    // ============================================
    console.log('%cOpenCitiVibes', 'font-size: 24px; font-weight: bold; color: #2563eb;');
    console.log('%cOpen Source Citizen Engagement Platform', 'font-size: 14px; color: #6b7280;');
    console.log('%chttps://github.com/opencitivibes/opencitivibes', 'font-size: 12px; color: #3b82f6;');

})();
