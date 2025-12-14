const { createApp } = Vue;

createApp({
    data() {
        return {
            activeTab: 'dashboard',
            stats: {},
            rules: [],
            history: [],
            monitors: {},
            conditionTypes: [],
            priorities: [],
            loading: false,
            
            // Filters
            filters: {
                rules: {
                    search: '',
                    db_name: '',
                    monitor_name: '',
                    active_only: true
                },
                monitors: {
                    search: '',
                    db_name: '',
                    show_disabled: true
                },
                history: {
                    search: '',
                    monitor_name: '',
                    db_name: ''
                }
            },
            
            // Rule form
            showRuleForm: false,
            editingRule: null,
            ruleForm: {
                name: '',
                monitor_name: '',
                db_name: '',
                condition_type: 'value_changed',
                condition_value: '',
                condition_duration: null,
                cooldown_seconds: 300,
                priority: 'medium',
                message_template: '🔔 {monitor_name}: {old_value} → {new_value}',
                target_chats: 'all',
                is_active: true
            },
            
            // Test form
            testForm: {
                old_value: '',
                new_value: ''
            },
            testResult: null
        }
    },
    
    async mounted() {
        await this.loadData();
        
        // Auto-refresh every 30 seconds
        setInterval(() => {
            if (this.activeTab === 'dashboard') {
                this.loadStats();
                this.loadMonitors();
            }
        }, 30000);
    },
    
    methods: {
        async loadData() {
            this.loading = true;
            try {
                await Promise.all([
                    this.loadStats(),
                    this.loadRules(),
                    this.loadHistory(),
                    this.loadMonitors(),
                    this.loadConditionTypes(),
                    this.loadPriorities()
                ]);
            } catch (error) {
                this.showError('Ошибка загрузки данных: ' + error.message);
            } finally {
                this.loading = false;
            }
        },
        
        async loadStats() {
            const response = await axios.get('/api/stats');
            this.stats = response.data;
        },
        
        async loadRules() {
            const params = new URLSearchParams();
            params.append('active_only', this.filters.rules.active_only);
            if (this.filters.rules.db_name) {
                params.append('db_name', this.filters.rules.db_name);
            }
            if (this.filters.rules.monitor_name) {
                params.append('monitor_name', this.filters.rules.monitor_name);
            }
            
            const response = await axios.get(`/api/rules?${params.toString()}`);
            this.rules = response.data;
        },
        
        async loadHistory() {
            const params = new URLSearchParams();
            params.append('limit', '50');
            if (this.filters.history.monitor_name) {
                params.append('monitor_name', this.filters.history.monitor_name);
            }
            
            const response = await axios.get(`/api/history?${params.toString()}`);
            this.history = response.data;
        },
        
        async loadMonitors() {
            const response = await axios.get('/api/monitors');
            this.monitors = response.data;
        },
        
        async loadConditionTypes() {
            const response = await axios.get('/api/condition-types');
            this.conditionTypes = response.data;
        },
        
        async loadPriorities() {
            const response = await axios.get('/api/priorities');
            this.priorities = response.data;
        },
        
        // Rule management
        showCreateRule() {
            this.editingRule = null;
            this.resetRuleForm();
            this.showRuleForm = true;
        },
        
        editRule(rule) {
            this.editingRule = rule;
            this.ruleForm = { ...rule };
            this.showRuleForm = true;
        },
        
        resetRuleForm() {
            this.ruleForm = {
                name: '',
                monitor_name: '',
                db_name: '',
                condition_type: 'value_changed',
                condition_value: '',
                condition_duration: null,
                cooldown_seconds: 300,
                priority: 'medium',
                message_template: '🔔 {monitor_name}: {old_value} → {new_value}',
                target_chats: 'all',
                is_active: true
            };
            this.testResult = null;
        },
        
        async saveRule() {
            try {
                if (this.editingRule) {
                    await axios.put(`/api/rules/${this.editingRule.id}`, this.ruleForm);
                    this.showSuccess('Правило успешно обновлено');
                } else {
                    await axios.post('/api/rules', this.ruleForm);
                    this.showSuccess('Правило успешно создано');
                }
                
                this.showRuleForm = false;
                await this.loadRules();
                await this.loadStats();
            } catch (error) {
                this.showError('Ошибка сохранения правила: ' + error.response?.data?.detail || error.message);
            }
        },
        
        async deleteRule(ruleId) {
            if (!confirm('Вы уверены, что хотите удалить это правило?')) {
                return;
            }
            
            try {
                await axios.delete(`/api/rules/${ruleId}`);
                this.showSuccess('Правило успешно удалено');
                await this.loadRules();
                await this.loadStats();
            } catch (error) {
                this.showError('Ошибка удаления правила: ' + error.response?.data?.detail || error.message);
            }
        },
        
        async toggleRule(rule) {
            try {
                await axios.put(`/api/rules/${rule.id}`, {
                    is_active: !rule.is_active
                });
                
                rule.is_active = !rule.is_active;
                this.showSuccess(`Правило ${rule.is_active ? 'включено' : 'отключено'}`);
            } catch (error) {
                this.showError('Ошибка изменения статуса правила: ' + error.response?.data?.detail || error.message);
            }
        },
        
        async testRule() {
            try {
                const response = await axios.post('/api/test-rule', {
                    ...this.ruleForm,
                    test_old_value: this.testForm.old_value,
                    test_new_value: this.testForm.new_value
                });
                
                this.testResult = response.data;
            } catch (error) {
                this.showError('Ошибка тестирования правила: ' + error.response?.data?.detail || error.message);
            }
        },
        
        // Utility methods
        formatDate(dateString) {
            if (!dateString) return 'Никогда';
            return new Date(dateString).toLocaleString();
        },
        
        formatDuration(seconds) {
            if (seconds < 60) return `${seconds}s`;
            if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
            const hours = Math.floor(seconds / 3600);
            const minutes = Math.floor((seconds % 3600) / 60);
            return `${hours}h ${minutes}m`;
        },
        
        getPriorityBadgeClass(priority) {
            const classes = {
                low: 'bg-secondary',
                medium: 'bg-primary',
                high: 'bg-warning',
                critical: 'bg-danger'
            };
            return classes[priority] || 'bg-secondary';
        },
        
        getConditionTypeLabel(type) {
            const condition = this.conditionTypes.find(ct => ct.value === type);
            return condition ? condition.label : type;
        },
        
        showSuccess(message) {
            // Simple success notification
            const alert = document.createElement('div');
            alert.className = 'alert alert-success alert-dismissible fade show position-fixed';
            alert.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
            alert.innerHTML = `
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;
            document.body.appendChild(alert);
            
            setTimeout(() => {
                if (alert.parentNode) {
                    alert.parentNode.removeChild(alert);
                }
            }, 5000);
        },
        
        showError(message) {
            // Simple error notification
            const alert = document.createElement('div');
            alert.className = 'alert alert-danger alert-dismissible fade show position-fixed';
            alert.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
            alert.innerHTML = `
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;
            document.body.appendChild(alert);
            
            setTimeout(() => {
                if (alert.parentNode) {
                    alert.parentNode.removeChild(alert);
                }
            }, 8000);
        },
        
        async forceTestNotification() {
            this.loading = true;
            try {
                const response = await axios.post('/api/force-test');
                if (response.data.success) {
                    this.showSuccess('✅ Тестовое уведомление отправлено: ' + response.data.message);
                } else {
                    this.showError('❌ Ошибка отправки: ' + response.data.error);
                }
            } catch (error) {
                this.showError('❌ Ошибка отправки тестового уведомления: ' + error.message);
            } finally {
                this.loading = false;
            }
        },
        
        async testAllRules() {
            this.loading = true;
            try {
                const response = await axios.post('/api/test-all-rules');
                if (response.data.success) {
                    this.showSuccess(`✅ Протестировано правил: ${response.data.tested_count}, сработало: ${response.data.triggered_count}`);
                } else {
                    this.showError('❌ Ошибка тестирования: ' + response.data.error);
                }
                // Refresh data after testing
                await this.loadHistory();
                await this.loadStats();
            } catch (error) {
                this.showError('❌ Ошибка тестирования правил: ' + error.message);
            } finally {
                this.loading = false;
            }
        },
        
        // Monitor management methods
        async disableMonitor(monitorName, dbName) {
            if (!confirm('Вы уверены, что хотите отключить все уведомления для этого монитора?')) {
                return;
            }
            
            this.loading = true;
            try {
                await axios.delete(`/api/monitors/${encodeURIComponent(monitorName)}/disable?db_name=${encodeURIComponent(dbName)}`);
                this.showSuccess('✅ Монитор отключен');
                await this.loadMonitors();
                await this.loadRules();
            } catch (error) {
                this.showError('❌ Ошибка отключения монитора: ' + error.message);
            } finally {
                this.loading = false;
            }
        },
        
        async enableMonitor(monitorName, dbName) {
            this.loading = true;
            try {
                await axios.post(`/api/monitors/${encodeURIComponent(monitorName)}/enable?db_name=${encodeURIComponent(dbName)}`);
                this.showSuccess('✅ Монитор включен');
                await this.loadMonitors();
                await this.loadRules();
            } catch (error) {
                this.showError('❌ Ошибка включения монитора: ' + error.message);
            } finally {
                this.loading = false;
            }
        },
        
        // Filter methods
        applyFilters() {
            this.loadRules();
            this.loadHistory();
        },
        
        clearFilters() {
            this.filters.rules = {
                search: '',
                db_name: '',
                monitor_name: '',
                active_only: true
            };
            this.filters.monitors = {
                search: '',
                db_name: '',
                show_disabled: true
            };
            this.filters.history = {
                search: '',
                monitor_name: '',
                db_name: ''
            };
            this.applyFilters();
        }
    },
    
    computed: {
        // Filtered data
        filteredRules() {
            return this.rules.filter(rule => {
                const searchMatch = !this.filters.rules.search || 
                    rule.name.toLowerCase().includes(this.filters.rules.search.toLowerCase()) ||
                    rule.monitor_name.toLowerCase().includes(this.filters.rules.search.toLowerCase());
                
                return searchMatch;
            });
        },
        
        filteredMonitors() {
            return Object.entries(this.monitors).filter(([key, monitor]) => {
                const searchMatch = !this.filters.monitors.search || 
                    monitor.monitor_name.toLowerCase().includes(this.filters.monitors.search.toLowerCase()) ||
                    monitor.db_name.toLowerCase().includes(this.filters.monitors.search.toLowerCase());
                
                const dbMatch = !this.filters.monitors.db_name || 
                    monitor.db_name === this.filters.monitors.db_name;
                    
                const disabledMatch = this.filters.monitors.show_disabled || !monitor.is_disabled;
                
                return searchMatch && dbMatch && disabledMatch;
            });
        },
        
        filteredHistory() {
            return this.history.filter(item => {
                const searchMatch = !this.filters.history.search || 
                    item.monitor_name.toLowerCase().includes(this.filters.history.search.toLowerCase()) ||
                    item.message.toLowerCase().includes(this.filters.history.search.toLowerCase());
                
                const dbMatch = !this.filters.history.db_name || 
                    item.db_name === this.filters.history.db_name;
                    
                const monitorMatch = !this.filters.history.monitor_name || 
                    item.monitor_name === this.filters.history.monitor_name;
                
                return searchMatch && dbMatch && monitorMatch;
            });
        },
        
        // Get unique database names for filter dropdowns
        uniqueDbNames() {
            const dbNames = new Set();
            this.rules.forEach(rule => dbNames.add(rule.db_name));
            Object.values(this.monitors).forEach(monitor => dbNames.add(monitor.db_name));
            return Array.from(dbNames).sort();
        },
        
        uniqueMonitorNames() {
            const monitorNames = new Set();
            this.rules.forEach(rule => monitorNames.add(rule.monitor_name));
            Object.values(this.monitors).forEach(monitor => monitorNames.add(monitor.monitor_name));
            return Array.from(monitorNames).sort();
        }
    },
    
    template: `
        <div class="container-fluid">
            <!-- Header -->
            <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
                <div class="container-fluid">
                    <span class="navbar-brand">
                        <i class="fas fa-database"></i>
                        Уведомления Монитора Базы Данных
                    </span>
                </div>
            </nav>
            
            <!-- Main Content -->
            <div class="row mt-3">
                <!-- Sidebar -->
                <div class="col-md-2">
                    <div class="nav flex-column nav-pills">
                        <button class="nav-link" :class="{active: activeTab === 'dashboard'}" 
                                @click="activeTab = 'dashboard'">
                            <i class="fas fa-chart-dashboard"></i> Панель
                        </button>
                        <button class="nav-link" :class="{active: activeTab === 'rules'}" 
                                @click="activeTab = 'rules'">
                            <i class="fas fa-cogs"></i> Правила
                        </button>
                        <button class="nav-link" :class="{active: activeTab === 'monitors'}" 
                                @click="activeTab = 'monitors'">
                            <i class="fas fa-eye"></i> Мониторы
                        </button>
                        <button class="nav-link" :class="{active: activeTab === 'history'}" 
                                @click="activeTab = 'history'">
                            <i class="fas fa-history"></i> История
                        </button>
                    </div>
                </div>
                
                <!-- Content -->
                <div class="col-md-10">
                    <!-- Dashboard Tab -->
                    <div v-if="activeTab === 'dashboard'">
                        <h2>Панель</h2>
                        
                        <!-- Stats Cards -->
                        <div class="row mb-4">
                            <div class="col-md-3">
                                <div class="card bg-primary text-white">
                                    <div class="card-body">
                                        <h5>Всего правил</h5>
                                        <h2>{{ stats.total_rules || 0 }}</h2>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-3">
                                <div class="card bg-success text-white">
                                    <div class="card-body">
                                        <h5>Активных правил</h5>
                                        <h2>{{ stats.active_rules || 0 }}</h2>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-3">
                                <div class="card bg-info text-white">
                                    <div class="card-body">
                                        <h5>Уведомлений (24ч)</h5>
                                        <h2>{{ stats.recent_notifications_24h || 0 }}</h2>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-3">
                                <div class="card bg-warning text-white">
                                    <div class="card-body">
                                        <h5>Успешность (7д)</h5>
                                        <h2>{{ stats.success_rate_7d || 0 }}%</h2>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Test Panel -->
                        <div class="card mb-4">
                            <div class="card-header">
                                <h5>🧪 Тестирование уведомлений</h5>
                            </div>
                            <div class="card-body">
                                <p class="text-muted">Отправить тестовое уведомление для проверки работы системы</p>
                                <button class="btn btn-warning me-2" @click="forceTestNotification" :disabled="loading">
                                    <i class="fas fa-rocket"></i> Отправить тестовое уведомление
                                </button>
                                <button class="btn btn-info" @click="testAllRules" :disabled="loading">
                                    <i class="fas fa-check-circle"></i> Протестировать все правила
                                </button>
                            </div>
                        </div>
                        
                        <!-- Recent Activity -->
                        <div class="card">
                            <div class="card-header">
                                <h5>Последние уведомления</h5>
                            </div>
                            <div class="card-body">
                                <div v-if="filteredHistory.length === 0" class="text-muted">
                                    Нет последних уведомлений
                                </div>
                                <div v-else>
                                    <div v-for="item in filteredHistory.slice(0, 5)" :key="item.id" 
                                         class="d-flex justify-content-between align-items-center border-bottom py-2">
                                        <div>
                                            <strong>{{ item.db_name }}.{{ item.monitor_name }}</strong>
                                            <br>
                                            <span class="text-muted">{{ item.message }}</span>
                                        </div>
                                        <div class="text-end">
                                            <small class="text-muted">{{ formatDate(item.sent_at) }}</small>
                                            <br>
                                            <span v-if="item.success" class="badge bg-success">✓</span>
                                            <span v-else class="badge bg-danger">✗</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Rules Tab -->
                    <div v-if="activeTab === 'rules'">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h2>Правила уведомлений</h2>
                            <button class="btn btn-primary" @click="showCreateRule">
                                <i class="fas fa-plus"></i> Создать правило
                            </button>
                        </div>
                        
                        <!-- Rules Filters -->
                        <div class="card mb-3">
                            <div class="card-body">
                                <h6 class="card-subtitle mb-3">🔍 Фильтры</h6>
                                <div class="row">
                                    <div class="col-md-3">
                                        <label class="form-label">Поиск</label>
                                        <input type="text" class="form-control" 
                                               v-model="filters.rules.search" 
                                               @input="applyFilters"
                                               placeholder="Название или монитор...">
                                    </div>
                                    <div class="col-md-3">
                                        <label class="form-label">База данных</label>
                                        <select class="form-select" 
                                                v-model="filters.rules.db_name" 
                                                @change="applyFilters">
                                            <option value="">Все базы</option>
                                            <option v-for="dbName in uniqueDbNames" :key="dbName" :value="dbName">
                                                {{ dbName }}
                                            </option>
                                        </select>
                                    </div>
                                    <div class="col-md-3">
                                        <label class="form-label">Монитор</label>
                                        <select class="form-select" 
                                                v-model="filters.rules.monitor_name" 
                                                @change="applyFilters">
                                            <option value="">Все мониторы</option>
                                            <option v-for="monitorName in uniqueMonitorNames" :key="monitorName" :value="monitorName">
                                                {{ monitorName }}
                                            </option>
                                        </select>
                                    </div>
                                    <div class="col-md-3">
                                        <label class="form-label">Статус</label>
                                        <div class="form-check mt-2">
                                            <input class="form-check-input" type="checkbox" 
                                                   v-model="filters.rules.active_only"
                                                   @change="applyFilters" id="activeOnly">
                                            <label class="form-check-label" for="activeOnly">
                                                Только активные
                                            </label>
                                        </div>
                                        <button class="btn btn-sm btn-outline-secondary mt-1" 
                                                @click="clearFilters">
                                            <i class="fas fa-times"></i> Сбросить
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Rules Table -->
                        <div class="card">
                            <div class="card-body">
                                <div v-if="rules.length === 0" class="text-muted text-center py-4">
                                    Правила не настроены. Создайте первое правило для начала работы!
                                </div>
                                <div v-else class="table-responsive">
                                    <table class="table table-striped">
                                        <thead>
                                            <tr>
                                                <th>Название</th>
                                                <th>Монитор</th>
                                                <th>Условие</th>
                                                <th>Приоритет</th>
                                                <th>Задержка</th>
                                                <th>Статус</th>
                                                <th>Действия</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            <tr v-for="rule in filteredRules" :key="rule.id">
                                                <td>{{ rule.name }}</td>
                                                <td>{{ rule.db_name }}.{{ rule.monitor_name }}</td>
                                                <td>{{ getConditionTypeLabel(rule.condition_type) }}</td>
                                                <td>
                                                    <span class="badge" :class="getPriorityBadgeClass(rule.priority)">
                                                        {{ rule.priority }}
                                                    </span>
                                                </td>
                                                <td>{{ formatDuration(rule.cooldown_seconds) }}</td>
                                                <td>
                                                    <span class="badge" :class="rule.is_active ? 'bg-success' : 'bg-secondary'">
                                                        {{ rule.is_active ? 'Активно' : 'Отключено' }}
                                                    </span>
                                                </td>
                                                <td>
                                                    <div class="btn-group btn-group-sm">
                                                        <button class="btn btn-outline-primary btn-sm" 
                                                                @click="editRule(rule)">
                                                            <i class="fas fa-edit"></i>
                                                        </button>
                                                        <button class="btn btn-outline-warning btn-sm" 
                                                                @click="toggleRule(rule)">
                                                            <i :class="rule.is_active ? 'fas fa-pause' : 'fas fa-play'"></i>
                                                        </button>
                                                        <button class="btn btn-outline-danger btn-sm" 
                                                                @click="deleteRule(rule.id)">
                                                            <i class="fas fa-trash"></i>
                                                        </button>
                                                    </div>
                                                </td>
                                            </tr>
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Monitors Tab -->
                    <div v-if="activeTab === 'monitors'">
                        <h2>Состояние мониторов</h2>
                        
                        <!-- Monitors Filters -->
                        <div class="card mb-3">
                            <div class="card-body">
                                <h6 class="card-subtitle mb-3">🔍 Фильтры</h6>
                                <div class="row">
                                    <div class="col-md-4">
                                        <label class="form-label">Поиск</label>
                                        <input type="text" class="form-control" 
                                               v-model="filters.monitors.search" 
                                               placeholder="Название монитора или БД...">
                                    </div>
                                    <div class="col-md-3">
                                        <label class="form-label">База данных</label>
                                        <select class="form-select" v-model="filters.monitors.db_name">
                                            <option value="">Все базы</option>
                                            <option v-for="dbName in uniqueDbNames" :key="dbName" :value="dbName">
                                                {{ dbName }}
                                            </option>
                                        </select>
                                    </div>
                                    <div class="col-md-3">
                                        <label class="form-label">Настройки</label>
                                        <div class="form-check mt-2">
                                            <input class="form-check-input" type="checkbox" 
                                                   v-model="filters.monitors.show_disabled" id="showDisabled">
                                            <label class="form-check-label" for="showDisabled">
                                                Показать отключенные
                                            </label>
                                        </div>
                                    </div>
                                    <div class="col-md-2">
                                        <label class="form-label">&nbsp;</label>
                                        <div>
                                            <button class="btn btn-outline-secondary btn-sm" 
                                                    @click="clearFilters">
                                                <i class="fas fa-times"></i> Сбросить
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <div class="card">
                            <div class="card-body">
                                <div v-if="Object.keys(monitors).length === 0" class="text-muted text-center py-4">
                                    В данный момент нет активных мониторов
                                </div>
                                <div v-else class="table-responsive">
                                    <table class="table table-striped">
                                        <thead>
                                            <tr>
                                                <th>Монитор</th>
                                                <th>Текущее значение</th>
                                                <th>Предыдущее значение</th>
                                                <th>Последнее изменение</th>
                                                <th>Длительность</th>
                                                <th>Статус</th>
                                                <th>Действия</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            <tr v-for="[key, monitor] in filteredMonitors" :key="key">
                                                <td>{{ monitor.db_name }}.{{ monitor.monitor_name }}</td>
                                                <td>
                                                    <code>{{ monitor.current_value }}</code>
                                                </td>
                                                <td>
                                                    <code>{{ monitor.previous_value }}</code>
                                                </td>
                                                <td>{{ formatDate(monitor.last_change_time) }}</td>
                                                <td>{{ formatDuration(monitor.same_value_duration) }}</td>
                                                <td>
                                                    <span v-if="monitor.is_disabled" class="badge bg-danger">
                                                        <i class="fas fa-ban"></i> Отключен
                                                    </span>
                                                    <span v-else class="badge bg-success">
                                                        <i class="fas fa-check"></i> Активен
                                                    </span>
                                                    <br>
                                                    <small class="text-muted">
                                                        Задержки: {{ monitor.active_cooldowns || 0 }}
                                                    </small>
                                                </td>
                                                <td>
                                                    <button v-if="monitor.is_disabled" 
                                                            class="btn btn-success btn-sm me-1"
                                                            @click="enableMonitor(monitor.monitor_name, monitor.db_name)"
                                                            :disabled="loading">
                                                        <i class="fas fa-play"></i> Включить
                                                    </button>
                                                    <button v-else 
                                                            class="btn btn-warning btn-sm me-1"
                                                            @click="disableMonitor(monitor.monitor_name, monitor.db_name)"
                                                            :disabled="loading">
                                                        <i class="fas fa-ban"></i> Отключить
                                                    </button>
                                                </td>
                                            </tr>
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- History Tab -->
                    <div v-if="activeTab === 'history'">
                        <h2>История уведомлений</h2>
                        
                        <!-- History Filters -->
                        <div class="card mb-3">
                            <div class="card-body">
                                <h6 class="card-subtitle mb-3">🔍 Фильтры</h6>
                                <div class="row">
                                    <div class="col-md-4">
                                        <label class="form-label">Поиск</label>
                                        <input type="text" class="form-control" 
                                               v-model="filters.history.search" 
                                               @input="applyFilters"
                                               placeholder="Сообщение или монитор...">
                                    </div>
                                    <div class="col-md-3">
                                        <label class="form-label">База данных</label>
                                        <select class="form-select" 
                                                v-model="filters.history.db_name" 
                                                @change="applyFilters">
                                            <option value="">Все базы</option>
                                            <option v-for="dbName in uniqueDbNames" :key="dbName" :value="dbName">
                                                {{ dbName }}
                                            </option>
                                        </select>
                                    </div>
                                    <div class="col-md-3">
                                        <label class="form-label">Монитор</label>
                                        <select class="form-select" 
                                                v-model="filters.history.monitor_name" 
                                                @change="applyFilters">
                                            <option value="">Все мониторы</option>
                                            <option v-for="monitorName in uniqueMonitorNames" :key="monitorName" :value="monitorName">
                                                {{ monitorName }}
                                            </option>
                                        </select>
                                    </div>
                                    <div class="col-md-2">
                                        <label class="form-label">&nbsp;</label>
                                        <div>
                                            <button class="btn btn-outline-secondary btn-sm" 
                                                    @click="clearFilters">
                                                <i class="fas fa-times"></i> Сбросить
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <div class="card">
                            <div class="card-body">
                                <div v-if="history.length === 0" class="text-muted text-center py-4">
                                    История уведомлений недоступна
                                </div>
                                <div v-else class="table-responsive">
                                    <table class="table table-striped">
                                        <thead>
                                            <tr>
                                                <th>Время</th>
                                                <th>Монитор</th>
                                                <th>Изменение</th>
                                                <th>Сообщение</th>
                                                <th>Статус</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            <tr v-for="item in filteredHistory" :key="item.id">
                                                <td>{{ formatDate(item.sent_at) }}</td>
                                                <td>{{ item.db_name }}.{{ item.monitor_name }}</td>
                                                <td>
                                                    <code>{{ item.old_value }}</code> →
                                                    <code>{{ item.new_value }}</code>
                                                </td>
                                                <td>{{ item.message }}</td>
                                                <td>
                                                    <span class="badge" :class="item.success ? 'bg-success' : 'bg-danger'">
                                                        {{ item.success ? 'Отправлено' : 'Ошибка' }}
                                                    </span>
                                                </td>
                                            </tr>
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Rule Form Modal -->
            <div class="modal" :class="{show: showRuleForm}" style="display: block;" v-if="showRuleForm">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                {{ editingRule ? 'Редактировать правило' : 'Создать новое правило' }}
                            </h5>
                            <button type="button" class="btn-close" @click="showRuleForm = false"></button>
                        </div>
                        <div class="modal-body">
                            <form @submit.prevent="saveRule">
                                <div class="row">
                                    <div class="col-md-6">
                                        <div class="mb-3">
                                            <label class="form-label">Название правила</label>
                                            <input type="text" class="form-control" v-model="ruleForm.name" required>
                                        </div>
                                    </div>
                                    <div class="col-md-3">
                                        <div class="mb-3">
                                            <label class="form-label">База данных</label>
                                            <input type="text" class="form-control" v-model="ruleForm.db_name" required>
                                        </div>
                                    </div>
                                    <div class="col-md-3">
                                        <div class="mb-3">
                                            <label class="form-label">Монитор</label>
                                            <input type="text" class="form-control" v-model="ruleForm.monitor_name" required>
                                        </div>
                                    </div>
                                </div>
                                
                                <div class="row">
                                    <div class="col-md-4">
                                        <div class="mb-3">
                                            <label class="form-label">Тип условия</label>
                                            <select class="form-select" v-model="ruleForm.condition_type">
                                                <option v-for="type in conditionTypes" :key="type.value" :value="type.value">
                                                    {{ type.label }}
                                                </option>
                                            </select>
                                        </div>
                                    </div>
                                    <div class="col-md-4">
                                        <div class="mb-3">
                                            <label class="form-label">Значение условия</label>
                                            <input type="text" class="form-control" v-model="ruleForm.condition_value" 
                                                   placeholder="Оставить пустым для некоторых условий">
                                        </div>
                                    </div>
                                    <div class="col-md-4">
                                        <div class="mb-3">
                                            <label class="form-label">Длительность (секунды)</label>
                                            <input type="number" class="form-control" v-model="ruleForm.condition_duration" 
                                                   placeholder="Для условий на основе времени">
                                        </div>
                                    </div>
                                </div>
                                
                                <div class="row">
                                    <div class="col-md-4">
                                        <div class="mb-3">
                                            <label class="form-label">Приоритет</label>
                                            <select class="form-select" v-model="ruleForm.priority">
                                                <option v-for="priority in priorities" :key="priority.value" :value="priority.value">
                                                    {{ priority.label }}
                                                </option>
                                            </select>
                                        </div>
                                    </div>
                                    <div class="col-md-4">
                                        <div class="mb-3">
                                            <label class="form-label">Задержка (секунды)</label>
                                            <input type="number" class="form-control" v-model="ruleForm.cooldown_seconds" required>
                                        </div>
                                    </div>
                                    <div class="col-md-4">
                                        <div class="mb-3">
                                            <label class="form-label">Целевые чаты</label>
                                            <input type="text" class="form-control" v-model="ruleForm.target_chats" 
                                                   placeholder="все или ID чатов">
                                        </div>
                                    </div>
                                </div>
                                
                                <div class="mb-3">
                                    <label class="form-label">Шаблон сообщения</label>
                                    <textarea class="form-control" v-model="ruleForm.message_template" rows="2" required></textarea>
                                    <div class="form-text">
                                        Доступные переменные: {monitor_name}, {db_name}, {old_value}, {new_value}, {timestamp}
                                    </div>
                                </div>
                                
                                <div class="mb-3">
                                    <div class="form-check">
                                        <input class="form-check-input" type="checkbox" v-model="ruleForm.is_active">
                                        <label class="form-check-label">Активно</label>
                                    </div>
                                </div>
                                
                                <!-- Test Section -->
                                <div class="border-top pt-3">
                                    <h6>Тестировать правило</h6>
                                    <div class="row">
                                        <div class="col-md-4">
                                            <input type="text" class="form-control" v-model="testForm.old_value" 
                                                   placeholder="Старое значение">
                                        </div>
                                        <div class="col-md-4">
                                            <input type="text" class="form-control" v-model="testForm.new_value" 
                                                   placeholder="Новое значение">
                                        </div>
                                        <div class="col-md-4">
                                            <button type="button" class="btn btn-outline-secondary" @click="testRule">
                                                Тестировать
                                            </button>
                                        </div>
                                    </div>
                                    
                                    <div v-if="testResult" class="mt-2">
                                        <div class="alert" :class="testResult.would_trigger ? 'alert-success' : 'alert-warning'">
                                            <strong>Результат:</strong> {{ testResult.would_trigger ? 'Сработает' : 'Не сработает' }}
                                            <br>
                                            <strong>Сообщение:</strong> {{ testResult.formatted_message }}
                                        </div>
                                    </div>
                                </div>
                            </form>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" @click="showRuleForm = false">Отмена</button>
                            <button type="button" class="btn btn-primary" @click="saveRule">
                                {{ editingRule ? 'Обновить' : 'Создать' }} правило
                            </button>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Loading Overlay -->
            <div v-if="loading" class="position-fixed top-0 start-0 w-100 h-100 d-flex align-items-center justify-content-center" 
                 style="background-color: rgba(0,0,0,0.5); z-index: 9999;">
                <div class="spinner-border text-light" role="status">
                    <span class="visually-hidden">Загрузка...</span>
                </div>
            </div>
        </div>
    `
}).mount('#app');