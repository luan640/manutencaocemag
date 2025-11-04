$(document).ready(function () {
    const table = $('#execucaoTable').DataTable({
        responsive: true,
        autoWidth: false,
        lengthMenu: [10, 25, 50, 100],
        pageLength: 10,
        processing: true,
        serverSide: true,
        ajax: {
            url: 'processa-historico/',
            type: 'POST',
            data: function (d) {
                // Adiciona os filtros personalizados aos dados enviados ao backend
                d.status = $('#filterStatus').val();
                // d.area = $('#filterArea').val();
                d.solicitante = $('#filterSolicitante').val();
                d.data_inicio = $('#filterDataInicio').val();
                d.ordem = $('#filterOrdem').val();
                d.setor = $('#filterSetor').val();
            }
        },
        columns: [
            { data: 'ordem' },
            { data: 'execucao' },
            { data: 'setor' },
            { data: 'solicitante' },
            { data: 'maquina' },
            { data: 'comentario_manutencao' },
            { data: 'motivo' },
            { data: 'data_abertura' },
            { data: 'data_inicio' },
            { data: 'data_fim' },
            { data: 'observacao' },
            { data: 'status' },
            { data: 'tipo_manutencao' },
            { data: 'area_manutencao' },
            { data: 'ultima_atualizacao' },
            { data: 'horas_executada' }
        ],
        language: {
            lengthMenu: "Exibir _MENU_ registros por página",
            zeroRecords: "Nenhuma execução encontrada",
            info: "Exibindo _START_ a _END_ de _TOTAL_ registros",
            infoEmpty: "Nenhum registro disponível",
            infoFiltered: "(filtrado de _MAX_ registros no total)"
        }
    });

    // Após inicializar a tabela
    loadColumnVisibility();

    // Adiciona checkboxes de colunas no menu
    const columnMenu = $('#columnToggleMenu');
    table.columns().every(function (index) {
        const column = this;
        const colName = column.header().textContent.trim();

        const checkbox = $(`
            <div class="form-check">
                <input class="form-check-input toggle-vis" type="checkbox" data-column="${index}" checked>
                <label class="form-check-label">${colName}</label>
            </div>
        `);

        columnMenu.append(checkbox);
    });

    // Evento de alternar visibilidade
    $('#columnToggleMenu').on('change', '.toggle-vis', function (e) {
        const column = table.column($(this).attr('data-column'));
        column.visible($(this).is(':checked'));

        // Salva no localStorage
        saveColumnVisibility();
    });

    $('#columnToggleMenu').on('click', function (e) {
        e.stopPropagation(); // evita fechar o menu
    });
  
    // Eventos para aplicar filtros
    $('#filterStatus, #filterArea, #filterSolicitante, #filterDataInicio, #filterOrdem, #filterSetor').on('change keyup', function () {
        table.ajax.reload(); // Recarrega os dados da tabela
    });

    $('#btnSelectAllColumns').click(function() {
        const $checkboxes = $('#columnToggleMenu input[type="checkbox"]');
        
         // Verifica se todos estão marcados
        const allChecked = $checkboxes.length === $checkboxes.filter(':checked').length;

        // Define o novo estado
        const newState = !allChecked;

        // Atualiza cada checkbox e dispara o evento change
        $checkboxes.each(function() {
            $(this).prop('checked', newState).trigger('change');
        });

        // Atualiza o texto do botão
        $(this).text(newState ? 'Desmarcar Todos' : 'Selecionar Todos');
    });

    // Função para salvar no localStorage
    function saveColumnVisibility() {
        const visibility = [];
        $('#columnToggleMenu input[type="checkbox"]').each(function() {
            visibility.push($(this).is(':checked'));
        });
        localStorage.setItem('execucaoTableColumns', JSON.stringify(visibility));
    }

    function loadColumnVisibility() {
        const saved = JSON.parse(localStorage.getItem('execucaoTableColumns'));
        if (saved && saved.length) {
            $('#columnToggleMenu input[type="checkbox"]').each(function(i) {
                $(this).prop('checked', saved[i]);
                table.column($(this).data('column-index')).visible(saved[i]);
            });
        }
    }

  });
