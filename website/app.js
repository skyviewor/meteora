const downloads = {
  "mac-arm64": {
    name: "macOS · Apple Silicon",
    file: "aero-macos-arm64.tar.gz",
  },
  "mac-x64": {
    name: "macOS · Intel",
    file: "aero-macos-x86_64.tar.gz",
  },
  "linux-x64": {
    name: "Linux · x86_64",
    file: "aero-linux-x86_64.tar.gz",
  },
  "linux-arm64": {
    name: "Linux · ARM64",
    file: "aero-linux-aarch64.tar.gz",
  },
};

async function detectPlatform() {
  const platform = (navigator.userAgentData?.platform || navigator.platform || "").toLowerCase();
  const agent = navigator.userAgent.toLowerCase();
  let architecture = "";

  if (navigator.userAgentData?.getHighEntropyValues) {
    const values = await navigator.userAgentData.getHighEntropyValues(["architecture"]);
    architecture = (values.architecture || "").toLowerCase();
  }
  if (!architecture) {
    if (/arm64|aarch64/.test(agent)) architecture = "arm";
    if (/x86_64|x86-64|amd64/.test(agent)) architecture = "x86";
  }

  if (platform.includes("mac") && architecture.includes("arm")) return "mac-arm64";
  if (platform.includes("mac") && architecture.includes("x86")) return "mac-x64";
  if (platform.includes("linux") && architecture.includes("arm")) return "linux-arm64";
  if (platform.includes("linux") && architecture.includes("x86")) return "linux-x64";
  return null;
}

async function configurePlatformDownload() {
  const key = await detectPlatform();
  const name = document.querySelector("#platform-name");
  const link = document.querySelector("#platform-download");
  const label = document.querySelector("#platform-download-label");
  if (!key || !downloads[key]) {
    name.textContent = "自动识别系统与架构";
    link.href = "https://aero.skyviewor.com/download/install.sh";
    label.textContent = "使用安装脚本";
    return;
  }

  const selected = downloads[key];
  name.textContent = selected.name;
  link.href = `https://aero.skyviewor.com/download/${selected.file}`;
  label.textContent = "下载分发包";
}

function configureCopyButton() {
  const button = document.querySelector("#copy-install");
  const command = document.querySelector("#install-command").textContent;
  const toast = document.querySelector("#copy-toast");
  let timer;

  button.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(command);
    } catch {
      const range = document.createRange();
      range.selectNodeContents(document.querySelector("#install-command"));
      window.getSelection().removeAllRanges();
      window.getSelection().addRange(range);
    }
    toast.classList.add("visible");
    clearTimeout(timer);
    timer = setTimeout(() => toast.classList.remove("visible"), 1800);
  });
}

configurePlatformDownload();
configureCopyButton();
window.lucide?.createIcons();
