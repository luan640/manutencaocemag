$(document).ready(function () {

  var userArea = $('#user-area').val();

  $('#maquinasCadastradas').DataTable({
    processing: true,
    serverSide: true,
    ajax: {
      url: 'processar',  // A URL que vai retornar os dados
      type: 'POST',
    },
    columns: [
      { data: 'codigo' },           // Código da máquina
      { data: 'descricao' },        // Descrição da máquina
      { data: 'apelido' },          // Apelido da máquina
      { data: 'setor' },            // Setor da máquina
      { data: 'foto',               // Foto
        render: function (data, type, row) {
          if (data) {
            return '<img src="' + data + '" alt="Foto" style="max-height: 50px; max-width: 50px;">';
          }
          return 'Sem foto';
        }
      },
      { data: 'area' },             // Área (Predial ou Produção)
      { data: 'tombamento' },       // Código de tombamento
      { data: 'criticidade' },      // Criticidade (A, B, C)
      {
        // Coluna de Editar e Criar Plano
        data: 'id',
        render: function (data, type, row) {
          if (userArea === 'predial'){

            return `
              <a href="/maquina/editar/${data}/" class="badge btn btn-sm btn-primary">
                <i class="fas fa-edit"></i>
              </a>
            `;

          } else {

            return `
                  <div class="d-flex justify-content-start">
                    <a href="/maquina/editar/${data}/" class="badge btn btn-sm btn-primary me-2">
                      <i class="fas fa-edit"></i>
                    </a>
                    <a href="/plano-preventiva/criar/${data}/" class="badge btn btn-sm btn-success">
                      <i class="fas fa-plus"></i>
                    </a>
                  </div>
                `;
          }
            
        },
        orderable: false,  // Desabilita a ordenação para esta coluna
        searchable: false  // Desabilita a busca para esta coluna
      },
    ],
    language: {
      search: "Procurar por código da máquina:"  // Personaliza a label do campo de busca
    }
  });
});
