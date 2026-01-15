$(document).ready(function () {

    let area = document.getElementById('area').value;
  
    const table = $('#preventivasTableHistorico').DataTable({
      processing: true,
      serverSide: true,
      ajax: {
          url: `/historico-preventiva/?area=${area}`,  // Adiciona o parâmetro como query string
          type: 'GET',
          data: function (d) {
              d.maquina = $('#filtroMaquinaHistorico').val(); // Adiciona o filtro de Máquina
              d.plano = $('#filtroPlanoHistorico').val(); // Adiciona o filtro de Plano
          },
      },
      columns: [
          { 
              data: 'codigo_maquina',
              render: function (data) {
                  return data ? `<span title="${data}">${truncateText(data, 20)}</span>` : 'N/A';
              }
          },
          { 
              data: 'descricao_maquina',
              render: function (data) {
                  return data ? `<span title="${data}">${truncateText(data, 30)}</span>` : 'N/A';
              }
          },
          { 
              data: 'nome_plano',
              render: function (data) {
                  return data ? `<span title="${data}">${truncateText(data, 30)}</span>` : 'N/A';
              }
          },
          { 
              data: 'data_finalizada',
              render: function (data) {
                  return data ? data : 'N/A';
              }
          }
      ],
      pageLength: 5,  // Define que a tabela terá 5 registros por página
      lengthChange: false,  // Desativa o seletor de número de registros por página
      autoWidth: false,  // Impede o DataTables de definir uma largura fixa
      responsive: true,  // Torna a tabela responsiva
      language: {
          paginate: {
              previous: "Anterior",
              next: "Próximo"
          }, 
          info: "Mostrando _START_ a _END_ de _TOTAL_ registros",  // Personaliza o texto de paginação
          zeroRecords: "Nenhum registro encontrado",  // Mensagem quando não há registros
          infoEmpty: "Mostrando 0 a 0 de 0 registros"
      },
      dom: 'lrtip'  // Remove o campo de pesquisa padrão ("f" foi removido)
  })
  
    // Função para truncar texto
    function truncateText(text, maxLength) {
      if (text.length > maxLength) {
        return text.substring(0, maxLength) + '...';
      }
      return text;
    }
  
    // Filtros
    $('#filtroMaquinaHistorico, #filtroPlanoHistorico').on('change', function () {
      table.ajax.reload(); // Recarrega a tabela quando o filtro muda
    });
  
    // Select2 para campos de filtros
    $('#filtroMaquinaHistorico').select2({
      placeholder: 'Selecione a Máquina',
      allowClear: true,
      ajax: {
          url: '/get-maquinas-preventiva/',
          dataType: 'json',
          delay: 250,
          data: function (params) {
              return {
                  search: params.term || '',
                  page: params.page || 1,
                  per_page: 10
              };
          },
          processResults: function (data, params) {
              params.page = params.page || 1;
              return {
                  results: data.results.map(item => ({
                      id: item.id,
                      text: item.text
                  })),
                  pagination: {
                      more: data.pagination.more
                  }
              };
          },
          cache: true
      },
      minimumInputLength: 0,
    });


    $('#filtroPlanoHistorico').select2({
    placeholder: 'Selecione o Plano',
    allowClear: true,
    ajax: {
        url: '/api/buscar-planos-preventiva/',
        dataType: 'json',
        delay: 250,
        language: 'pt-BR',
        data: function (params) {
            return {
                search: params.term || '',
                page: params.page || 1,
                per_page: 10
            };
        },
        processResults: function (data, params) {
            params.page = params.page || 1;
            return {
                results: data.results.map(item => ({
                    id: item.id,
                    text: item.text
                })),
                pagination: {
                    more: data.pagination.more
                }
            };
        },
        cache: true
    },
    minimumInputLength: 0,
  });
    
  });
  
  