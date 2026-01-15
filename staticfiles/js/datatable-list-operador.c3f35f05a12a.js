export async function carregarTabela() {
  if ($.fn.DataTable.isDataTable("#tableOperadores")) {
    $("#tableOperadores").DataTable().clear().destroy()
  }

  const overlayLoading = document.getElementById("overlayLoading")
  overlayLoading.style.display = "flex"
  
  await fetch("/api/operadores/")
    .then((response) => response.json())
    .then((data) => {
      const tbody = document.querySelector("#tableOperadores tbody")
      tbody.innerHTML = ""
      data.operadores.forEach((operador) => {
        const row = `
          <tr data-id="${operador.id}">
              <td id="operadorNome-${operador.id}"><strong>${operador.nome}</strong></td>
              <td id="operadorMatricula-${operador.id}">${operador.matricula}</td>
              <td id="operadorStatus-${operador.id}">
                <span class="badge ${operador.status === "ativo" ? "bg-success" : "bg-secondary"}">
                  ${operador.status}
                </span>
              </td>
              <td id="operadorArea-${operador.id}">${operador.area}</td>
              <td>
                <button class="btn btn-warning btn-sm btnEditOperador me-1" id="btnEditOperador-${operador.id}">
                  <i class="bi bi-pencil"></i> Editar
                </button>
                <button class="btn btn-danger btn-sm btnDesativarOperador" id="btnDesativarOperador-${operador.id}">
                  <i class="bi bi-x-circle"></i> Desativar
                </button>
              </td>
          </tr>`
        tbody.insertAdjacentHTML("beforeend", row)
      })

      overlayLoading.style.display = "none"

      const table = $("#tableOperadores").DataTable({
        info: true,
        autoWidth: false,
        responsive: true,
        processing: true,
        pagingType: "simple_numbers",
        colReorder: true,
        fixedHeader: true,
        lengthMenu: [10, 25, 50, 100],
        pageLength: 10,
        language: { url: "//cdn.datatables.net/plug-ins/1.13.7/i18n/pt-BR.json" },
        dom: "lrtip", // Remove default search box
        createdRow: (row) => {
          row.addEventListener("mouseenter", () => {
            row.style.backgroundColor = "#f8f9ff"
          })
          row.addEventListener("mouseleave", () => {
            row.style.backgroundColor = ""
          })
        },
      })

      $("#searchOperadores").on("keyup", function () {
        table.search(this.value).draw()
      })
    })
}

// Chama no carregamento inicial
// document.addEventListener("DOMContentLoaded", carregarTabela);
