// Добавляем точку при нажатии клавиши Enter, чтобы не приходилось тыкать мышью
document.addEventListener("DOMContentLoaded", () => {
  console.log(document.getElementById("enter-point"));
  document
    .getElementById("enter-point")
    .addEventListener("keypress", function (event) {
      if (event.key === "Enter") {
        event.preventDefault();
        document.getElementById("add-btn").click();
      }
    });
});
