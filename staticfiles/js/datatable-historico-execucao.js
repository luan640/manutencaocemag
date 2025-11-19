$(document).ready(function () {

    let filtrosEstado = {};

    const table = $('#execucaoTable').DataTable({
        lengthChange: false,
        searching: false,
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

                // Grupo 1: Identificação da Ordem 
                d.ordem = $('#filterOrdem').val();
                d.execucao = $('#filterExecucao').val();
                d.setor = $('#filterSetor').val();
                d.solicitante = $('#filterSolicitante').val();
                d.operador = $('#filterOperadores').val();
                d.area = $('#filterArea').val();

                // Grupo 2: Máquina e Manutenção
                d.maquina = $('#filterMaquina').val();
                d.tipoManutencao = $('#filterTipoManutencao').val();
                d.areaManutencao = $('#filterAreaManutencao').val();
                d.horasExecutadasInicial = $('#filterHorasExecutadasInicial').val();
                d.horasExecutadasFinal = $('#filterHorasExecutadasFinal').val();

                // Grupo 3: Datas
                d.dataAberturaInicial = $('#filterDataAberturaInicial').val();
                d.dataAberturaFinal = $('#filterDataAberturaFinal').val();
                d.dataInicioInicial = $('#filterDataInicioInicial').val();
                d.dataInicioFinal = $('#filterDataInicioFinal').val();
                d.dataFinalInicial = $('#filterDataFinalInicial').val();
                d.dataFinalFinal = $('#filterDataFinalFinal').val();
                d.ultimaAtualizacaoInicial = $('#filterUltimaAtualizacaoInicial').val();
                d.ultimaAtualizacaoFinal = $('#filterUltimaAtualizacaoFinal').val();
                
                // Grupo 4: Comentários e Status
                d.comentarioManutencao = $('#filterComentarioManutencao').val();
                d.motivo = $('#filterMotivo').val();
                d.obsExecutante = $('#filterObsExecutante').val();
                d.status = $('#filterStatus').val();
            },
        },
        columns: [
            { data: 'ordem' },
            { data: 'execucao' },
            { data: 'setor' },
            { data: 'solicitante' },
            { data: 'maquina' },
            { data: 'comentario_manutencao' },
            { data: 'motivo' },
            { data: 'operadores'},
            { data: 'area'},
            { data: 'data_abertura' },
            { data: 'data_inicio' },
            { data: 'data_fim' },
            { data: 'observacao' },
            { data: 'status' },
            { data: 'tipo_manutencao' },
            { data: 'area_manutencao' },
            { data: 'ultima_atualizacao' },
            { data: 'horas_executada' },
        ],
        language: {
            zeroRecords: "Nenhuma execução encontrada",
            info: "Exibindo _START_ a _END_ de _TOTAL_ registros",
            infoEmpty: "Nenhum registro disponível",
            infoFiltered: "(filtrado de _MAX_ registros no total)"
        }
    });


    // Atualiza cards de indicadores quando os dados são carregados
    table.on('xhr.dt', function (e, settings, json) {
        const total = json && json.recordsTotal != null ? json.recordsTotal : 0;
        const filtrado = json && json.recordsFiltered != null ? json.recordsFiltered : total;

        $('#kpiTotalExecucoes').text(total);
        $('#kpiExecucoesFiltradas').text(filtrado);
    });

    // Atualiza soma de horas da página atual
    table.on('draw', function () {
        let totalMinutos = 0;

        function parseHoras(str) {
            if (!str) return 0;
            const partes = String(str).split(':');
            if (partes.length < 2) return 0;
            const h = parseInt(partes[0], 10) || 0;
            const m = parseInt(partes[1], 10) || 0;
            return h * 60 + m;
        }

        table.column(17, { page: 'current' }).data().each(function (valor) {
            totalMinutos += parseHoras(valor);
        });

        const horas = Math.floor(totalMinutos / 60);
        const minutos = totalMinutos % 60;
        const formatado =
            String(horas).padStart(2, '0') + ':' +
            String(minutos).padStart(2, '0');

        $('#kpiHorasPagina').text(formatado);
    });


    // Adiciona checkboxes de colunas no menu
    const columnMenu = $('#columnToggleMenu');
    table.columns().every(function (index) {
        const column = this;
        const colName = column.header().textContent.trim();

        const checkbox = $(`
            <div class="form-check">
                <input class="form-check-input toggle-vis" type="checkbox" data-column="${index}" data-name="${colName}" checked>
                <label class="form-check-label">${colName}</label>
            </div>
        `);

        columnMenu.append(checkbox);
        filtrosEstado[colName] = true;

    });


    // Após inicializar a tabela
    loadColumnVisibility();

    // Evento de alternar visibilidade
    $('#columnToggleMenu').on('change', '.toggle-vis', function (e) {
        const column = table.column($(this).attr('data-column'));
        const columnName = $(this).attr('data-name');
        const status = $(this).is(':checked')
        column.visible(status);
        filtrosEstado[columnName] = status;

        // Pegar o nome da coluna
        // Procurar no menu dropdown de filtros pelo filtro dessa coluna
        const $filtroItem = $(`#filtrosMenu .filter-item[data-name="${columnName}"]`);
        const $filtroCampo = $filtroItem.find('input', 'select');

        if ($filtroItem.length) {
            $filtroItem.css('display', status ? '' : 'none');
            $filtroCampo.prop('disabled', !status);
        }

        // Habilitar ou desabilitar filtro de acordo com o valor do checkbox
        // Salva no localStorage
        saveColumnVisibility();
    });

    $('#columnToggleMenu').on('click', function (e) {
        e.stopPropagation(); // evita fechar o menu
    });

    $('#btnLimparFiltro').on('click', function(){
        var btn = $(this);
        var btnFiltrar = $('#btnFiltrarEnvio');

        btn.prop('disabled', true).text('Limpando...');
        btnFiltrar.prop('disabled', true)

        $(`#filtrosMenu .filter-item`).each(function(){
            const campo = $(this).find('input, select');

            campo.each(function(){
                if (this.tagName === 'SELECT') {
                    // limpa selects (inclusive múltiplos)
                    $(this).val(null).trigger('change'); // <-- ESSENCIAL para Select2
                    this.selectedIndex = -1;
                if (this.multiple) {
                    $(this).find('option').prop('selected', false);
                }
                // seta "Todos" se existir
                if ($(this).find('option[value=""]').length) {
                    $(this).val('');
                }
                } else {
                    // limpa inputs (text, number, date etc.)
                    $(this).val('');

                    // remove restrições se for um campo de data
                    if (this.type === 'date') {
                        this.removeAttribute('min');
                        this.removeAttribute('max');
                    }
                }
            })
        });
        table.ajax.reload(function(){
            btn.prop('disabled', false).text('Limpar Filtros');
            btnFiltrar.prop('disabled', false);
        }, false); // Recarrega os dados da tabela
        atualizarFiltrosAtivos();
    })

    $('#btnFiltrarEnvio').on('click', function(){
        var btn = $(this);
        var btnLimparFiltro = $('#btnLimparFiltro');
        btn.prop('disabled', true).text('Filtrando...');
        btnLimparFiltro.prop('disabled', true);

        table.ajax.reload(function(){
            btn.prop('disabled', false).text('Filtrar');
            btnLimparFiltro.prop('disabled', false);
        }, false); // Recarrega os dados da tabela
        atualizarFiltrosAtivos();
    })

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

    $('#filtrosMenu').on('click', function(e) {
        e.stopPropagation();
    });

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
            placeholder: 'Selecione o Status',
            allowClear: true,
            width: '100%',
            closeOnSelect: false,   // <--- essencial: não fecha ao selecionar
            ajax: {
                url: '/api/status-execucao/', // ajuste se sua rota for diferente
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
                const results = (data.status || []).map(s => ({
                    id: s.status,
                    text: `${s.status || ''}`
                }));
                return {
                    results: results
                };
                },
                cache: true
            },
        });
        
        $('#filterSetor').select2({
            placeholder: 'Selecione o Setor',
            allowClear: true,
            width: '100%',
            closeOnSelect: false,   // <--- essencial: não fecha ao selecionar
            ajax: {
                url: '/api/setores/', // ajuste se sua rota for diferente
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
                const results = (data.setores || []).map(s => ({
                    id: s.id,
                    text: `${s.nome || ''}`
                }));
                return {
                    results: results
                };
                },
                cache: true
            },
        });

        $('#filterTipoManutencao').select2({
            placeholder: 'Selecione o Tipo',
            allowClear: true,
            width: '100%',
            closeOnSelect: false,   // <--- essencial: não fecha ao selecionar
            ajax: {
                url: '/api/tipo-manutencao/', // ajuste se sua rota for diferente
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
                const results = (data.tiposManutencao || []).map(s => ({
                    id: s.tipo_manutencao,
                    text: `${s.tipo_manutencao || ''}`
                }));
                return {
                    results: results
                };
                },
                cache: true
            },
        });

        $('#filterOperadores').select2({
            language: 'pt-BR',
            placeholder: 'Buscar operadores...',
            minimumInputLength: 1,
            allowClear: true,
            ajax: {
                url: '/api/operadores/', // ajuste se sua rota for diferente
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
                const results = (data.operadores || []).map(op => ({
                    id: op.id,
                    text: `${op.matricula} - ${op.nome || ''}`
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

        $('#filterAreaManutencao').select2({
            placeholder: 'Selecione a Área',
            allowClear: true,
            width: '100%',
            closeOnSelect: false,   // <--- essencial: não fecha ao selecionar
        });

        $('#filterHorasExecutadasInicial, #filterHorasExecutadasFinal').on('blur', function(){
            formatarInput(this);
        });

        $('#btnFecharFiltros').on('click', function() {
            // pega a instância do dropdown
            const $dropdownBtn = $('#btnFiltros');
            if ($dropdownBtn){
                const dropdownInstance = bootstrap.Dropdown.getOrCreateInstance($dropdownBtn);
                dropdownInstance.hide(); // fecha o dropdown
            }
            
        });
        // Impede datas inválidas
        bindDateRange('filterHorasExecutadasInicial', 'filterHorasExecutadasFinal')
        bindDateRange('filterDataAberturaInicial', 'filterDataAberturaFinal');
        bindDateRange('filterDataInicioInicial', 'filterDataInicioFinal');
        bindDateRange('filterDataFinalInicial', 'filterDataFinalFinal');
        bindDateRange('filterUltimaAtualizacaoInicial', 'filterUltimaAtualizacaoFinal');


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

                    const columnName = $(this).attr('data-name');
                    const status = $(this).is(':checked')

                    // Carregar os filtros de acordo com os checkboxes das colunas
                    const $filtroItem = $(`#filtrosMenu .filter-item[data-name="${columnName}"]`);
                    const $filtroCampo = $filtroItem.find('input', 'select');
                    filtrosEstado[columnName] = status;

                    if ($filtroItem.length) {
                        $filtroItem.css('display', status ? '' : 'none');
                        $filtroCampo.prop('disabled', !status);
                    }
                });
            }
        }

        function formatarInput(input) {
            // Remove tudo que não seja número
            let valor = input.value.replace(/\D/g, '');
    
            if (valor.length === 0){
                return;
            } else if (valor.length <= 2){
                input.value = `${valor}:00`
            } else{
                let horas = valor.length > 2 ? valor.slice(0, valor.length - 2) : '0';
                let minutos = valor.slice(-2);

                // Ajusta minutos se passar de 59
                if (parseInt(minutos) > 59) minutos = '59';

                input.value = `${parseInt(horas)}:${minutos.padStart(2, '0')}`; 
            }          
        }

        function atualizarFiltrosAtivos() {
            const filtrosAtivos = [];

            $('#filtrosMenu .filter-item').each(function () {
                const label = $(this).find('label').first().text().trim();
                const inputs = $(this).find('input, select');
                let valor = '';

                // --- Campo único ---
                if (inputs.length === 1) {
                const input = inputs.first();

                if (input.is('select')) {
                    // Se for select simples ou múltiplo, pegar o texto da opção
                    const selecionadas = input.find('option:selected').map(function () {
                    return $(this).text().trim();
                    }).get();

                    valor = selecionadas.filter(v => v !== '' && v.toLowerCase() !== 'todos').join(', ');
                } else {
                    valor = input.val();
                }
                }

                // --- Intervalo (ex: Início / Fim) ---
                else if (inputs.length === 2) {
                    const v1 = $(inputs[0]).val();
                    const v2 = $(inputs[1]).val();

                    if (v1 || v2) {
                        if (v1 && v2) valor = `${v1} até ${v2}`;
                        else if (v1) valor = `a partir de ${v1}`;
                        else valor = `até ${v2}`;
                    }
                }

                // --- Adicionar se tiver algo preenchido ---
                if (valor && valor !== '') {
                filtrosAtivos.push(`<span class="badge bg-primary text-white">${label}: ${valor}</span>`);
                }
            });

            // --- Atualizar o HTML ---
            if (filtrosAtivos.length > 0) {
                $('#filtrosAtivos').html(filtrosAtivos.join(' '));
            } else {
                $('#filtrosAtivos').html('<span class="text-muted">Nenhum filtro aplicado</span>');
            }
            }

        // Vínculo entre datas inicial e final: define `min` no campo final quando a inicial muda
        function bindDateRange(initialId, finalId) {
            const init = document.getElementById(initialId);
            const fin = document.getElementById(finalId);
            if (!init || !fin) return;

            const applyMinFromInit = () => {
                // define o menor valor permitido no final
                fin.min = init.value || '';
                // se o valor atual do final for anterior ao mínimo, ajusta para o mínimo
                if (init.value && fin.value && fin.value < init.value) {
                    fin.value = init.value;
                }
            };

            const applyMaxFromFin = () => {
                init.max = fin.value || '';
                if (fin.value && init.value && init.value > fin.value) {
                    init.value = fin.value;
                }
            };

            // Eventos
            init.addEventListener('blur', applyMinFromInit);
            fin.addEventListener('blur', applyMaxFromFin);

            // sincroniza no carregamento (caso haja valores preenchidos pelo servidor)
            applyMinFromInit();
            applyMaxFromFin();

        }

        // 🔽 Botão para exportar Excel
        $('#btnExportarExcel').click(function() {
            var btn = $(this);
            var btnFiltrarEnvio = $('#btnFiltrarEnvio');
            var btnLimparFiltros = $('#btnLimparFiltro');

            btnFiltrarEnvio.prop('disabled', true);
            btnLimparFiltros.prop('disabled', true);

            btn.prop('disabled', true).text('Exportando...');

            // Reaproveita os mesmos filtros do DataTables
            let filtros = table.ajax.params(); // pega os filtros atuais
            filtros.exportar_xlsx = 1;         // flag para o backend gerar o Excel
            // filtros.csrfmiddlewaretoken = '{{ csrf_token }}';
            filtros.filtrosEstado = filtrosEstado;

            $.ajax({
                url: 'processa-historico/',
                type: 'POST',
                data: filtros,
                xhrFields: { responseType: 'blob' },
                success: function(blob) {
                    let url = window.URL.createObjectURL(blob);
                    let a = document.createElement('a');
                    a.href = url;
                    a.download = "execucoes.xlsx";
                    document.body.appendChild(a);
                    a.click();
                    a.remove();
                },
                complete: function() {
                    btn.prop('disabled', false).text('Exportar Excel');
                    btnFiltrarEnvio.prop('disabled', false);
                    btnLimparFiltros.prop('disabled', false);
                },
                error: function() {
                    alert('Erro ao exportar o arquivo Excel');
                }
            });
        });

  });
