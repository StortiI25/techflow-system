const root=document.documentElement;
const saved=localStorage.getItem("estoqueflow_theme")||"dark";
root.setAttribute("data-theme",saved);
function updateThemeButton(){
  document.querySelectorAll("#themeToggle").forEach(btn=>{
    const dark=root.getAttribute("data-theme")==="dark";
    btn.innerHTML=dark?'<i class="bi bi-sun"></i><span> Modo claro</span>':'<i class="bi bi-moon-stars"></i><span> Modo escuro</span>';
  });
}
updateThemeButton();
document.addEventListener("click",e=>{
  if(e.target.closest("#themeToggle")){
    const next=root.getAttribute("data-theme")==="dark"?"light":"dark";
    root.setAttribute("data-theme",next);
    localStorage.setItem("estoqueflow_theme",next);
    updateThemeButton();
  }
});
document.addEventListener("DOMContentLoaded",()=>{
  const menuBtn=document.getElementById("menuBtn");
  const sidebar=document.getElementById("sidebar");
  const overlay=document.getElementById("mobileOverlay");
  if(menuBtn&&sidebar&&overlay){
    menuBtn.addEventListener("click",()=>{sidebar.classList.toggle("active");overlay.classList.toggle("active")});
    overlay.addEventListener("click",()=>{sidebar.classList.remove("active");overlay.classList.remove("active")});
  }
});
