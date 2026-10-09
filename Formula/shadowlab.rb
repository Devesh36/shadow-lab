class Shadowlab < Formula
  desc "Local application security investigations with inspectable evidence"
  homepage "https://github.com/Devesh36/shadow-lab"
  license "MIT"
  head "https://github.com/Devesh36/shadow-lab.git", branch: "feature/browser-identity-validation"

  depends_on "node"
  depends_on "python@3.12"
  depends_on "uv"
  uses_from_macos "git"

  def install
    libexec.install Dir["*", ".github"]
    ENV["UV_CACHE_DIR"] = buildpath/"uv-cache"
    system Formula["uv"].opt_bin/"uv", "sync", "--locked", "--no-dev",
           "--python", Formula["python@3.12"].opt_bin/"python3.12", "--project", libexec
    bin.install_symlink libexec/".venv/bin/shadow"
    bin.install_symlink libexec/".venv/bin/shadowlab"
  end

  def caveats
    <<~EOS
      Open the console with: shadow repl
      Choose Demo to prepare and investigate the bundled synthetic local application.
      First setup downloads locked Node dependencies. Chromium is optional for browser validation.
      This HEAD formula installs the current feature branch; no stable release is published yet.
    EOS
  end

  test do
    assert_match "repl", shell_output("#{bin}/shadow --help")
    assert_match "ShadowLab closed", pipe_output("#{bin}/shadow Repl", "quit\n", 0)
  end
end
