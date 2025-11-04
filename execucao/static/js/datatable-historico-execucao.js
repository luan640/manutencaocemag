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

    // Após inicializar a tabela
    loadColumnVisibility();

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
    // filtros(OS, Setor, Solicitante, Máquina, Data Abertura, Data Inicio, Data Fim, Status)
    $('#filterStatus, #filterSolicitante, #filterDataInicio, #filterOrdem, #filterSetor').on('change keyup', function () {
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
                table.column($(this).data('column')).visible(saved[i]);
            });
        }
    }

    $('#filterMaquina').select2({
            language: 'pt-BR',
            placeholder: 'Buscar máquina por código ou descrição...',
            minimumInputLength: 1,
            allowClear: true,
            ajax: {
                url: '/api/maquinas/', // ajuste se sua rota for diferente
                dataType: 'json',
                delay: 250, // debounce
                data: function (params) {
                // params.term = texto digitado
                return {
                    search: params.term,    // nossa API usa 'search'
                    limit: 25               // quantos resultados queremos (padrão do backend)
                    // se mais tarde implementar paginação: enviar page: params.page
                };
                },
                processResults: function (data /*, params */) {
                // sua API retorna data.maquinas = [{id, codigo, descricao}, ...]
                const results = (data.maquinas || []).map(m => ({
                    id: m.id,
                    text: `${m.codigo} - ${m.descricao || ''}`
                }));
                return {
                    results: results
                    // se implementar paginação, retornar também pagination: { more: <boolean> }
                };
                },
                cache: true
            },
            templateResult: function (item) {
                if (!item.id) { return item.text; } // placeholder/loading
                return $('<span>').text(item.text);
            },
            templateSelection: function (item) {
                return item.text || item.id;
            },
            escapeMarkup: function (m) { return m; },
            width: '100%'
        });

        // Aplicando Select2 para multiplo select de status no filtro
        $('#filterStatus').select2({
            placeholder: 'Selecione status',
            allowClear: true,
            width: '100%',
            closeOnSelect: false,   // <--- essencial: não fecha ao selecionar
        });

  });
