let tableMaq;

$(document).ready(function () {
    const userArea = $('#user-area').val();

    // Inicializa DataTables com configurações
    tableMaq = $('#maquinasCadastradas').DataTable({
        responsive: true,
        autoWidth: false,
        lengthMenu: [10, 25, 50, 100],
        pageLength: 10,
        processing: true,
        serverSide: true,
        ajax: {
            url: 'processar',
            type: 'POST',
            data: function (d) {
                d.maquina = $('#filterMaquina').val();
                d.criticidade = $('#filterCriticidade').val();
                d.maquina_critica = $('#filterMaquinaCritica').val();
                d.setor = $('#filterSetor').val();
            },
        },
        dom: 'lrtip', // 👈 remove a barra de busca padrão
        columns: [
            { data: 'codigo' },
            { data: 'descricao' },
            { data: 'apelido' },
            { data: 'setor' },
            { data: 'tipo' },
            {
                data: 'foto',
                render: function (data) {
                    return data
                        ? `<img src="${data}" alt="Foto" style="max-height: 50px; max-width: 50px;">`
                        : 'Sem foto';
                }
            },
            { data: 'area' },
            { data: 'tombamento' },
            { data: 'criticidade' },
            { data: 'maquina_critica' },
            {
                data: 'id',
                render: function (data, type, row) {
                    // Botões diferentes para Predial ou Produção
                    if (userArea === 'predial') {
                        return `
                            <button type="button" class="btn btn-sm btn-primary" onclick="editarMaquina(this)" data-id="${data}">
                                <i class="fas fa-edit"></i>
                            </button>
                        `;
                    } else {
                        return `
                            <div class="d-flex justify-content-start">
                                <button type="button" class="btn btn-sm btn-warning me-2" onclick="editarMaquina(this)" data-id="${data}">
                                    <i class="fas fa-edit"></i>
                                </button>

                                <button type="button" class="btn btn-sm btn-success" onclick="criarPlanoPreventiva(this)" data-id="${data}" data-codigo="${row.codigo}" data-descricao="${row.descricao}">
                                  <i class="fas fa-plus"></i>
                                </button>
                            </div>  
                        `;
                    }
                },
                orderable: false,
                searchable: false
            },
        ],
        language: {
            search: "Buscar:",
            lengthMenu: "Mostrar _MENU_ registros por página",
            zeroRecords: "Nenhuma máquina encontrada",
            info: "Mostrando página _PAGE_ de _PAGES_",
            infoEmpty: "Nenhum dado disponível",
            infoFiltered: "(filtrado de _MAX_ registros no total)",
            paginate: {
                previous: "Anterior",
                next: "Próximo"
            },
        }
    });

    // Integra o campo de busca externo com o DataTable
    $('#searchMaquinas').on('keyup', function () {
        tableMaq.search(this.value).draw();
    });

    $('#filterMaquina, #filterCriticidade, #filterMaquinaCritica, #filterSetor').on('change', function () {
        tableMaq.ajax.reload();
    });

    $('#btnLimparFiltrosMaquina').on('click', function () {
        $('#filterMaquina').val(null).trigger('change');
        $('#filterCriticidade').val('');
        $('#filterMaquinaCritica').val('');
        $('#filterSetor').val('');
        tableMaq.ajax.reload();
    });

    carregarFiltrosMaquina();

    // Opcional: mostrar overlay de loading (se desejar usar visualmente)
    // tableMaq.on('processing.dt', function (e, settings, processing) {
    //     $('#overlayLoading').toggle(processing);
    //     // $('#overlayLoading').css('display', processing ? 'flex' : 'none');
    // });
});

function carregarFiltrosMaquina() {
    inicializarSelectMaquina();

    fetch('/api/maquinas-list/')
        .then(response => response.json())
        .then(data => {
            const select = document.getElementById('filterMaquina');
            if (!select) return;
            (data.maquinas || []).forEach(maquina => {
                const option = document.createElement('option');
                option.value = maquina.id;
                option.textContent = `${maquina.codigo} - ${maquina.descricao}`;
                select.appendChild(option);
            });
        })
        .catch(error => console.error('Erro ao carregar maquinas:', error));

    fetch('/api/setores/')
        .then(response => response.json())
        .then(data => {
            const select = document.getElementById('filterSetor');
            if (!select) return;
            (data.setores || []).forEach(setor => {
                const option = document.createElement('option');
                option.value = setor.id;
                option.textContent = setor.nome;
                select.appendChild(option);
            });
        })
        .catch(error => console.error('Erro ao carregar setores:', error));
}

function inicializarSelectMaquina() {
    const $select = $('#filterMaquina');
    if (!$select.length) return;
    if ($select.data('select2')) return;

    $select.select2({
        placeholder: 'Todas',
        allowClear: true,
        width: '100%',
        language: 'pt-BR'
    });
}
