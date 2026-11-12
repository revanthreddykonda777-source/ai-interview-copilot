// ============================================================
// three_bg.js — Shared Three.js Scene, Framer Motion & Lucide
// ============================================================

const { useEffect, useRef } = React;

// Safe Framer Motion bindings (graceful fallback if CDN unavailable)
const _MotionLib = window.Motion || {};
const motion = _MotionLib.motion || new Proxy({}, {
  get: (_, tag) => (props) => {
    const {
      initial, animate, exit, transition, whileHover, whileTap,
      whileInView, viewport, layout, variants, ...domProps
    } = props || {};
    return React.createElement(tag, domProps);
  }
});
const AnimatePresence = _MotionLib.AnimatePresence || (({ children }) => <>{children}</>);
const EASE_OUT = [0.22, 1, 0.36, 1];

// Pure-React Lucide Icon wrapper using window.lucide
function LucideIcon({ name, size = 18, strokeWidth = 1.85, className = "", style = {} }) {
  const node = window.lucide && window.lucide[name];
  if (!Array.isArray(node)) return null;
  const [, , children = []] = node;
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={`lucide-icon ${className}`}
      style={{ flexShrink: 0, display: "inline-block", ...style }}
      aria-hidden="true"
    >
      {children.map(([tag, attrs], idx) => React.createElement(tag, { key: idx, ...attrs }))}
    </svg>
  );
}

// Interactive Three.js Architectural Geometry Backdrop
function ThreeBackground({ dimmed = false, theme = "light" }) {
  const mountRef = useRef(null);

  useEffect(() => {
    const container = mountRef.current;
    if (!container || !window.THREE) return;

    const THREE = window.THREE;
    let renderer;
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    } catch (e) {
      return; // WebGL unavailable
    }

    const prefersReduced =
      typeof window.matchMedia === "function" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    const isDark = theme === "dark";
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 100);
    camera.position.z = 9;

    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setClearColor(0x000000, 0);
    container.appendChild(renderer.domElement);

    const group = new THREE.Group();
    group.position.set(2.9, 0.15, 0);
    scene.add(group);

    // Warm studio 3-point lighting for genuine 3D sculptural depth
    const ambientLight = new THREE.AmbientLight(isDark ? 0xffe8d6 : 0xfff8f0, isDark ? 0.7 : 0.9);
    scene.add(ambientLight);

    const keyLight = new THREE.DirectionalLight(0xfff5ea, isDark ? 1.5 : 1.3);
    keyLight.position.set(5, 6, 7);
    scene.add(keyLight);

    const rimWarm = new THREE.PointLight(0xea580c, isDark ? 2.6 : 1.8, 22);
    rimWarm.position.set(-4, -2, 5);
    scene.add(rimWarm);

    const rimTeal = new THREE.PointLight(0x0f766e, isDark ? 2.0 : 1.4, 22);
    rimTeal.position.set(5, -4, 4);
    scene.add(rimTeal);

    // Sculpted 3D faceted solid core + crisp metallic edge cage
    const icoGeo = new THREE.IcosahedronGeometry(2.15, 1);
    const icoSolidMat = new THREE.MeshStandardMaterial({
      color: isDark ? 0x2b241f : 0xf2e9dc,
      roughness: 0.36,
      metalness: 0.32,
      flatShading: true,
      transparent: true,
      opacity: isDark ? 0.42 : 0.46
    });
    const polySolid = new THREE.Mesh(icoGeo, icoSolidMat);
    group.add(polySolid);

    const icoWire = new THREE.WireframeGeometry(icoGeo);
    const icoMat = new THREE.LineBasicMaterial({
      color: isDark ? 0xea580c : 0xc2410c,
      transparent: true,
      opacity: isDark ? 0.34 : 0.28
    });
    const poly = new THREE.LineSegments(icoWire, icoMat);
    polySolid.add(poly);

    // Inner brushed brass octahedron jewel
    const innerGeo = new THREE.OctahedronGeometry(1.02, 0);
    const innerSolidMat = new THREE.MeshStandardMaterial({
      color: isDark ? 0xd97706 : 0xb45309,
      roughness: 0.25,
      metalness: 0.72,
      flatShading: true,
      transparent: true,
      opacity: isDark ? 0.55 : 0.5
    });
    const innerPoly = new THREE.Mesh(innerGeo, innerSolidMat);
    const innerWire = new THREE.WireframeGeometry(innerGeo);
    const innerMat = new THREE.LineBasicMaterial({
      color: isDark ? 0xfef3c7 : 0x181614,
      transparent: true,
      opacity: isDark ? 0.25 : 0.22
    });
    innerPoly.add(new THREE.LineSegments(innerWire, innerMat));
    group.add(innerPoly);

    // Classic interlocking 3D astrolabe gimbal rings
    const ringGeo = new THREE.TorusGeometry(3.05, 0.038, 16, 100);
    const ringMat = new THREE.MeshStandardMaterial({
      color: isDark ? 0x14b8a6 : 0x0f766e,
      roughness: 0.3,
      metalness: 0.65,
      transparent: true,
      opacity: isDark ? 0.48 : 0.42
    });
    const ring = new THREE.Mesh(ringGeo, ringMat);
    ring.rotation.x = Math.PI * 0.36;
    ring.rotation.y = Math.PI * 0.14;
    group.add(ring);

    const ring2Geo = new THREE.TorusGeometry(3.55, 0.024, 14, 100);
    const ring2Mat = new THREE.MeshStandardMaterial({
      color: isDark ? 0xa8a29e : 0x78716c,
      roughness: 0.35,
      metalness: 0.55,
      transparent: true,
      opacity: isDark ? 0.35 : 0.32
    });
    const ring2 = new THREE.Mesh(ring2Geo, ring2Mat);
    ring2.rotation.x = -Math.PI * 0.28;
    ring2.rotation.y = Math.PI * 0.42;
    group.add(ring2);

    // Subtle spatial particle field
    const count = 75;
    const positions = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      positions[i * 3] = (Math.random() - 0.5) * 18;
      positions[i * 3 + 1] = (Math.random() - 0.5) * 11;
      positions[i * 3 + 2] = (Math.random() - 0.5) * 6;
    }
    const ptsGeo = new THREE.BufferGeometry();
    ptsGeo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    const ptsMat = new THREE.PointsMaterial({
      color: isDark ? 0xa8a29e : 0x78716c,
      size: 0.045,
      transparent: true,
      opacity: isDark ? 0.3 : 0.35
    });
    const points = new THREE.Points(ptsGeo, ptsMat);
    scene.add(points);

    const mouse = { x: 0, y: 0, tx: 0, ty: 0 };
    const onMove = (e) => {
      mouse.tx = (e.clientX / window.innerWidth - 0.5) * 2;
      mouse.ty = (e.clientY / window.innerHeight - 0.5) * 2;
    };
    if (!prefersReduced) {
      window.addEventListener("mousemove", onMove, { passive: true });
    }

    const onResize = () => {
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
      if (prefersReduced) renderer.render(scene, camera);
    };
    window.addEventListener("resize", onResize);

    let rafId;
    const clock = new THREE.Clock();
    const animate = () => {
      rafId = requestAnimationFrame(animate);
      const t = clock.getElapsedTime();
      const scrollY = window.scrollY || 0;
      const scrollRatio = Math.min(1.5, scrollY / Math.max(1, window.innerHeight));

      mouse.x += (mouse.tx - mouse.x) * 0.04;
      mouse.y += (mouse.ty - mouse.y) * 0.04;

      polySolid.rotation.y = t * 0.12 + mouse.x * 0.35 + scrollRatio * 1.1;
      polySolid.rotation.x = t * 0.08 + mouse.y * 0.25 + scrollRatio * 0.55;

      innerPoly.rotation.y = -t * 0.22 - scrollRatio * 0.9;
      innerPoly.rotation.z = t * 0.14;

      ring.rotation.z = t * 0.08 + scrollRatio * 0.7;
      ring.rotation.x = Math.PI * 0.36 + mouse.y * 0.12;
      ring2.rotation.z = -t * 0.05 - scrollRatio * 0.5;
      ring2.rotation.y = Math.PI * 0.42 + mouse.x * 0.14;
      group.rotation.y = mouse.x * 0.08;
      group.rotation.x = mouse.y * 0.06;
      group.position.y = 0.15 - scrollRatio * 0.85;
      points.rotation.y = t * 0.015 + mouse.x * 0.05;
      points.rotation.x = mouse.y * 0.04;

      renderer.render(scene, camera);
    };

    if (prefersReduced) {
      renderer.render(scene, camera);
    } else {
      animate();
    }

    return () => {
      if (rafId) cancelAnimationFrame(rafId);
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("resize", onResize);
      icoGeo.dispose(); icoWire.dispose(); icoMat.dispose();
      innerGeo.dispose(); innerWire.dispose(); innerMat.dispose();
      ringGeo.dispose(); ringMat.dispose();
      ptsGeo.dispose(); ptsMat.dispose();
      renderer.dispose();
      if (renderer.domElement.parentNode === container) {
        container.removeChild(renderer.domElement);
      }
    };
  }, [theme]);

  return (
    <div
      ref={mountRef}
      className={`three-canvas-wrap ${dimmed ? "is-dimmed" : ""}`}
      aria-hidden="true"
    />
  );
}

Object.assign(window, { motion, AnimatePresence, EASE_OUT, LucideIcon, ThreeBackground });

