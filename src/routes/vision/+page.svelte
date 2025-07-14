<script lang="ts">
  import { onMount } from 'svelte';
  let videoEl: HTMLVideoElement;
  let speed = 0;
  let angle = 0;
  let hsvText = "Click the ball to sample color";
  let pc: RTCPeerConnection | null = null;
  

  async function startWebRTC() {
    // Clean up old connection if it exists
    if (pc) {
      console.log("[RTC] Cleaning up old connection...");
      pc.getSenders().forEach((s) => s.track?.stop());
      pc.close();
      pc = null;
    }

    pc = new RTCPeerConnection();

    // 👇 This tells the browser "I want to receive video"
    pc.addTransceiver("video", { direction: "recvonly" });

    pc.ontrack = (event) => {
      const stream = event.streams[0];
      if (videoEl) {
        videoEl.srcObject = stream;
      }
    };

    const offer = await pc.createOffer();
    await pc.setLocalDescription(offer);

    const res = await fetch("http://192.168.88.194:8000/offer", {
      method: "POST",
      body: JSON.stringify({
        sdp: pc.localDescription?.sdp,
        type: pc.localDescription?.type,
      }),
      headers: {
        "Content-Type": "application/json",
      },
    });

    const answer = await res.json();
    await pc.setRemoteDescription(answer);
  }



  async function pollTelemetry() {
    const res = await fetch('http://localhost:8000/api/ball_stats');
    const data = await res.json();
    speed = data.speed_mps;
    angle = data.angle_deg;
  }

  onMount(() => {
    startWebRTC();
    const interval = setInterval(pollTelemetry, 1000);
    return () => clearInterval(interval);
  });


  async function onVideoClick(event: MouseEvent) {
    if (!videoEl) return;

    const rect = videoEl.getBoundingClientRect();
    const scaleX = videoEl.videoWidth / rect.width;
    const scaleY = videoEl.videoHeight / rect.height;

    const x = Math.round((event.clientX - rect.left) * scaleX);
    const y = Math.round((event.clientY - rect.top) * scaleY);

    console.log("Click at video pixel:", x, y);

    try {
      const res = await fetch(`http://localhost:8000/api/sample_pixel?x=${x}&y=${y}`);
      const data = await res.json();

      if (data.h !== undefined) {
        hsvText = `Sampled HSV: H=${data.h}, S=${data.s}, V=${data.v}`;
      } else {
        hsvText = "Error: " + (data.error || "Unknown error");
      }
    } catch (err) {
      console.error(err);
      hsvText = "Error: Failed to fetch pixel";
    }
  }
  
</script>

<div class="video-container">
  <video bind:this={videoEl} autoplay playsinline muted on:click={onVideoClick}></video>
  <div class="overlay">
    <div>Speed: {speed} m/s</div>
    <div>Angle: {angle}°</div>
    <div>Color: {hsvText}</div>
  </div>
</div>



<style>
  .video-container {
    position: relative;
    width: 80%;
    height: 90vh; /* full screen height */
    background: black;
    margin: 0 auto;
  }

  video {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    object-fit: cover; /* fill container without distortion */
  }

  .overlay {
    position: absolute;
    top: 20px;
    left: 20px;
    padding: 8px 14px;
    background: rgba(0, 0, 0, 0.6);
    color: white;
    font-size: 1rem;
    font-weight: 600;
    border-radius: 4px;
    z-index: 10;
    pointer-events: none;
  }
</style>
