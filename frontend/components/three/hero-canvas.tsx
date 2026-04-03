"use client";
import { useEffect, useRef } from "react";
import * as THREE from "three";
export function HeroCanvas() {
  const mountRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = mountRef.current;
    if (!el) return;
    const W = el.clientWidth, H = el.clientHeight;
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(W, H);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.domElement.style.width  = "100%";
    renderer.domElement.style.height = "100%";
    el.appendChild(renderer.domElement);
    const scene  = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(50, W / H, 0.1, 100);
    camera.position.set(0, 0, 10);
    const amb  = new THREE.AmbientLight(0xffffff, 0.45);
    const key  = new THREE.DirectionalLight(0xfff8f0, 1.8); key.position.set(8, 14, 8);
    const fill = new THREE.DirectionalLight(0xf0f8ff, 0.4); fill.position.set(-8, -4, 5);
    scene.add(amb, key, fill);
    const docMesh = new THREE.Mesh(new THREE.BoxGeometry(2.0, 2.65, 0.06), new THREE.MeshPhysicalMaterial({ color: 0xffffff, metalness: 0.0, roughness: 0.04, clearcoat: 1.0, clearcoatRoughness: 0.02 }));
    docMesh.position.set(3.4, 0.3, 0); scene.add(docMesh);
    const lineData: [number, number, number][] = [
      [0xFF9F0A, 1.4, 0.9],[0xe8e8ed, 1.2, 0.63],[0xe8e8ed, 0.95, 0.36],
      [0xe8e8ed, 1.15, 0.09],[0xe8e8ed, 0.80, -0.18],[0xf0f0f0, 1.05, -0.45],
    ];
    lineData.forEach(([c, w, y]) => { const m = new THREE.Mesh(new THREE.BoxGeometry(w, 0.034, 0.012), new THREE.MeshBasicMaterial({ color: c })); m.position.set(3.4, y, 0.045); scene.add(m); });
    const sphere = new THREE.Mesh(new THREE.SphereGeometry(0.75, 64, 64), new THREE.MeshPhysicalMaterial({ color: 0xFF9F0A, metalness: 0.55, roughness: 0.14, clearcoat: 0.7, clearcoatRoughness: 0.12 }));
    sphere.position.set(-3.4, 1.7, 0.4); scene.add(sphere);
    const torus  = new THREE.Mesh(new THREE.TorusGeometry(1.2, 0.035, 8, 72),  new THREE.MeshBasicMaterial({ color: 0xFF9F0A, transparent: true, opacity: 0.22 }));
    torus.position.set(0.4, -1.8, -2.0); scene.add(torus);
    const torus2 = new THREE.Mesh(new THREE.TorusGeometry(0.62, 0.024, 8, 52), new THREE.MeshBasicMaterial({ color: 0xFFD60A, transparent: true, opacity: 0.16 }));
    torus2.position.set(-2.8, -1.3, 0.9); torus2.rotation.x = Math.PI / 2.4; scene.add(torus2);
    const oct = new THREE.Mesh(new THREE.OctahedronGeometry(0.55, 0), new THREE.MeshPhysicalMaterial({ color: 0x1d1d1f, metalness: 0.92, roughness: 0.07 }));
    oct.position.set(-3.5, -1.5, 0.7); scene.add(oct);
    const ico = new THREE.Mesh(new THREE.IcosahedronGeometry(0.5, 0), new THREE.MeshBasicMaterial({ color: 0xffffff, wireframe: true, transparent: true, opacity: 0.08 }));
    ico.position.set(3.2, -2.0, 0.9); scene.add(ico);
    const pCount = 280;
    const pPositions = new Float32Array(pCount * 3).map(() => (Math.random() - 0.5) * 24);
    const pGeo = new THREE.BufferGeometry();
    pGeo.setAttribute("position", new THREE.BufferAttribute(pPositions, 3));
    const particles = new THREE.Points(pGeo, new THREE.PointsMaterial({ color: 0xFF9F0A, size: 0.042, transparent: true, opacity: 0.38 }));
    scene.add(particles);
    const mouse = { x: 0, y: 0 };
    const onMouse = (e: MouseEvent) => { mouse.x = (e.clientX / window.innerWidth - 0.5) * 2; mouse.y = -(e.clientY / window.innerHeight - 0.5) * 2; };
    window.addEventListener("mousemove", onMouse);
    let raf: number;
    const t0 = Date.now();
    const tick = () => {
      raf = requestAnimationFrame(tick);
      const t = (Date.now() - t0) * 0.001;
      docMesh.rotation.y = Math.sin(t * 0.38) * 0.17 + mouse.x * 0.09;
      docMesh.rotation.x = Math.sin(t * 0.28) * 0.055 + mouse.y * 0.055;
      docMesh.position.y = 0.3 + Math.sin(t * 0.6) * 0.17;
      sphere.rotation.y = t * 0.46; sphere.rotation.x = t * 0.26;
      sphere.position.y = 1.7 + Math.sin(t * 0.72) * 0.28;
      oct.rotation.x = t * 0.62; oct.rotation.y = t * 0.44;
      oct.position.y = -1.5 + Math.sin(t * 1.0) * 0.22;
      torus.rotation.x = t * 0.2; torus.rotation.y = t * 0.3; torus.rotation.z = t * 0.15;
      torus2.rotation.y = t * 0.48; torus2.rotation.z = t * 0.26;
      ico.rotation.x = t * 0.36; ico.rotation.y = t * 0.52;
      particles.rotation.y = t * 0.02; particles.rotation.x = t * 0.008;
      camera.position.x += (mouse.x * 0.6  - camera.position.x) * 0.03;
      camera.position.y += (mouse.y * 0.35 - camera.position.y) * 0.03;
      camera.lookAt(0, 0, 0);
      renderer.render(scene, camera);
    };
    tick();
    const onResize = () => { const W2 = el.clientWidth, H2 = el.clientHeight; camera.aspect = W2 / H2; camera.updateProjectionMatrix(); renderer.setSize(W2, H2); };
    window.addEventListener("resize", onResize);
    return () => { cancelAnimationFrame(raf); window.removeEventListener("mousemove", onMouse); window.removeEventListener("resize", onResize); renderer.dispose(); if (el.contains(renderer.domElement)) el.removeChild(renderer.domElement); };
  }, []);
  return <div ref={mountRef} style={{ position: "absolute", inset: 0, width: "100%", height: "100%", zIndex: 0 }} />;
}
