// ============================================================
// auth_motion.js — Scroll Animations, 3D Backdrop & Form Polish
// ============================================================
(function () {
  const prefersReduced =
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // 1. Password visibility toggle buttons
  document.querySelectorAll("[data-toggle-password]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const targetId = btn.getAttribute("data-toggle-password");
      const input = document.getElementById(targetId);
      if (!input) return;
      const show = input.type === "password";
      input.type = show ? "text" : "password";
      btn.setAttribute("aria-label", show ? "Hide password" : "Show password");
      btn.classList.toggle("is-visible", show);
    });
  });

  // 2. Top Scroll Progress Bar
  const progressBar = document.getElementById("scroll-progress-bar");
  const updateScrollProgress = () => {
    if (!progressBar) return;
    const maxScroll = Math.max(1, document.documentElement.scrollHeight - window.innerHeight);
    const pct = Math.min(100, Math.max(0, (window.scrollY / maxScroll) * 100));
    progressBar.style.width = pct + "%";
  };
  window.addEventListener("scroll", updateScrollProgress, { passive: true });
  updateScrollProgress();

  // 3. IntersectionObserver Scroll-Reveal Stagger
  const revealEls = document.querySelectorAll(".scroll-reveal");
  if (prefersReduced || !("IntersectionObserver" in window)) {
    revealEls.forEach((el) => el.classList.add("is-visible"));
  } else {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.14, rootMargin: "0px 0px -30px 0px" }
    );
    revealEls.forEach((el) => observer.observe(el));
  }

  // 4. Three.js 3D Architectural Backdrop with Scroll Parallax
  const mount = document.getElementById("auth-three-bg");
  if (!mount || !window.THREE) return;

  const THREE = window.THREE;
  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  } catch (e) {
    return;
  }

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(44, window.innerWidth / window.innerHeight, 0.1, 100);
  camera.position.z = 9.5;

  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.setClearColor(0x000000, 0);
  mount.appendChild(renderer.domElement);

  scene.add(new THREE.AmbientLight(0xfff8f0, 0.9));
  const key = new THREE.DirectionalLight(0xfff5ea, 1.35);
  key.position.set(5, 6, 7);
  scene.add(key);

  const rimWarm = new THREE.PointLight(0xea580c, 1.9, 22);
  rimWarm.position.set(-4, -2, 5);
  scene.add(rimWarm);

  const rimTeal = new THREE.PointLight(0x0f766e, 1.5, 22);
  rimTeal.position.set(5, -3, 4);
  scene.add(rimTeal);

  const group = new THREE.Group();
  group.position.set(-2.6, 0.25, 0);
  scene.add(group);

  const icoGeo = new THREE.IcosahedronGeometry(2.05, 1);
  const polySolid = new THREE.Mesh(
    icoGeo,
    new THREE.MeshStandardMaterial({
      color: 0xf2e9dc,
      roughness: 0.35,
      metalness: 0.3,
      flatShading: true,
      transparent: true,
      opacity: 0.44
    })
  );
  polySolid.add(
    new THREE.LineSegments(
      new THREE.WireframeGeometry(icoGeo),
      new THREE.LineBasicMaterial({ color: 0xc2410c, transparent: true, opacity: 0.28 })
    )
  );
  group.add(polySolid);

  const innerPoly = new THREE.Mesh(
    new THREE.OctahedronGeometry(0.95, 0),
    new THREE.MeshStandardMaterial({
      color: 0xb45309,
      roughness: 0.25,
      metalness: 0.72,
      flatShading: true,
      transparent: true,
      opacity: 0.48
    })
  );
  group.add(innerPoly);

  const ring = new THREE.Mesh(
    new THREE.TorusGeometry(2.95, 0.036, 16, 100),
    new THREE.MeshStandardMaterial({
      color: 0x0f766e,
      roughness: 0.3,
      metalness: 0.65,
      transparent: true,
      opacity: 0.42
    })
  );
  ring.rotation.x = Math.PI * 0.36;
  ring.rotation.y = Math.PI * 0.14;
  group.add(ring);

  const onResize = () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
    if (prefersReduced) renderer.render(scene, camera);
  };
  window.addEventListener("resize", onResize);

  const mouse = { x: 0, y: 0, tx: 0, ty: 0 };
  if (!prefersReduced) {
    window.addEventListener(
      "mousemove",
      (e) => {
        mouse.tx = (e.clientX / window.innerWidth - 0.5) * 2;
        mouse.ty = (e.clientY / window.innerHeight - 0.5) * 2;
      },
      { passive: true }
    );
  }

  const clock = new THREE.Clock();
  const animate = () => {
    requestAnimationFrame(animate);
    const t = clock.getElapsedTime();
    const scrollProgress = Math.min(1, window.scrollY / Math.max(1, window.innerHeight));

    mouse.x += (mouse.tx - mouse.x) * 0.04;
    mouse.y += (mouse.ty - mouse.y) * 0.04;

    polySolid.rotation.y = t * 0.12 + mouse.x * 0.32 + scrollProgress * 1.4;
    polySolid.rotation.x = t * 0.08 + mouse.y * 0.22 + scrollProgress * 0.7;
    innerPoly.rotation.y = -t * 0.22 - scrollProgress * 1.1;
    ring.rotation.z = t * 0.08 + scrollProgress * 0.9;
    group.position.y = 0.25 - scrollProgress * 1.2;

    renderer.render(scene, camera);
  };

  if (prefersReduced) {
    renderer.render(scene, camera);
  } else {
    animate();
  }
})();

