// $(document).ready(function() {
//   $('#tableOperadores').DataTable({
//       "info": true,             // Informação sobre os registros
//       "autoWidth": false,       // Desativa ajuste automático da largura
//       "responsive": true        // Responsividade
//   });
// });

export async function carregarTabela() {

  if ( $.fn.DataTable.isDataTable('#tableOperadores') ) {
      $('#tableOperadores').DataTable().clear().destroy();
  }

  document.getElementById('overlayLoading').style.display = 'block';

  await fetch('/api/operadores/')
    .then(response => response.json())
    .then(data => {
      const tbody = document.querySelector('#tableOperadores tbody');
      tbody.innerHTML = '';
      data.operadores.forEach(operador => {
        const row = `
          <tr data-id="${operador.id}">
              <td id="operadorNome-${ operador.id }">${ operador.nome }</td>
              <td id="operadorMatricula-${ operador.id }">${ operador.matricula }</td>
              <td id="operadorSalario-${ operador.id }">${ operador.salario }</td>
              <td id="operadorStatus-${ operador.id }">${ operador.status }</td>
              <td id="operadorArea-${ operador.id }">${ operador.area }</td>
              <td>
                  <span class="badge btn btn-warning" id="btnEditOperador-${ operador.id }">Editar</span>
                  <span class="badge btn btn-danger" id="btnDesativarOperador-${ operador.id }">Desativar</span>
              </td>
          </tr>`;
        tbody.insertAdjacentHTML('beforeend', row);
      });

      document.getElementById('overlayLoading').style.display = 'none';

      $('#tableOperadores').DataTable({
        "info": true,
        "autoWidth": false,
        "responsive": true,
        "processing": true
      });
    });
}

// Chama no carregamento inicial
// document.addEventListener("DOMContentLoaded", carregarTabela);


