/*
  Behaviour:
  - Connect to ws://127.0.0.1:8765
  - Receive messages like { type: 'audio', speaking: bool, amplitude: 0..1 }
  - Animate a centered circle based on amplitude.

  Notes for non-coders:
  - "amplitude" is loudness. We use it to scale and lift the circle.
  - If the connection drops, we retry every few seconds.
*/

(function () {
  const ball = document.getElementById('ball');

  let targetAmp = 0; // Incoming amplitude from backend
  let currentAmp = 0; // Smoothed amplitude for motion

  function connect() {
    const ws = new WebSocket('ws://127.0.0.1:8765');

    ws.addEventListener('open', () => {
      console.log('UI connected to backend.');
    });

    ws.addEventListener('message', (evt) => {
      try {
        const msg = JSON.parse(evt.data);
        if (msg.type === 'audio') {
          // Clamp to safe range
          targetAmp = Math.max(0, Math.min(1, Number(msg.amplitude || 0)));
          if (msg.speaking) {
            ball.classList.add('speaking');
          } else {
            ball.classList.remove('speaking');
            targetAmp = 0;
          }
        }
      } catch (e) {
        console.warn('Bad message from backend', e);
      }
    });

    ws.addEventListener('close', () => {
      console.log('Backend disconnected; retrying soon...');
      setTimeout(connect, 2000);
    });

    ws.addEventListener('error', () => ws.close());
  }

  // Animation loop: ease towards targetAmp to keep motion smooth
  function animate() {
    // Simple critically-damped ease
    const easing = 0.12;
    currentAmp += (targetAmp - currentAmp) * easing;

    // Map amplitude to motion: translate up to 30px and scale up to 1.25x
    const lift = -30 * currentAmp;
    const scale = 1 + currentAmp * 0.25;
    ball.style.transform = `translateY(${lift}px) scale(${scale})`;

    requestAnimationFrame(animate);
  }

  connect();
  animate();
})();


