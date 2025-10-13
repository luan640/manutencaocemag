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

    // Opcional: mostrar overlay de loading (se desejar usar visualmente)
    // tableMaq.on('processing.dt', function (e, settings, processing) {
    //     $('#overlayLoading').toggle(processing);
    //     // $('#overlayLoading').css('display', processing ? 'flex' : 'none');
    // });
});
