const root=document.documentElement;const saved=localStorage.getItem("techflow_theme")||"dark";root.setAttribute("data-theme",saved);
function upd(){document.querySelectorAll("#themeToggle").forEach(b=>{let d=root.getAttribute("data-theme")==="dark";b.innerHTML=d?'<i class="bi bi-sun"></i><span>Modo claro</span>':'<i class="bi bi-moon-stars"></i><span>Modo escuro</span>'})}
upd();document.addEventListener("click",e=>{if(e.target.closest("#themeToggle")){let n=root.getAttribute("data-theme")==="dark"?"light":"dark";root.setAttribute("data-theme",n);localStorage.setItem("techflow_theme",n);upd();location.reload();}})


document.addEventListener("DOMContentLoaded", () => {
  const menuBtn = document.querySelector(".menu-btn");
  const sidebar = document.querySelector(".sidebar");
  const overlay = document.getElementById("mobileOverlay");

  if(menuBtn && sidebar && overlay){
    menuBtn.addEventListener("click", () => {
      sidebar.classList.toggle("active");
      overlay.classList.toggle("active");
    });

    overlay.addEventListener("click", () => {
      sidebar.classList.remove("active");
      overlay.classList.remove("active");
    });

    sidebar.querySelectorAll("a").forEach(link => {
      link.addEventListener("click", () => {
        sidebar.classList.remove("active");
        overlay.classList.remove("active");
      });
    });
  }
});
