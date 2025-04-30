// static/js/auth.js
// Funciones para manejar la autenticación JWT en el cliente

/**
 * Clase para gestionar la autenticación con JWT
 */
class AuthManager {
    constructor() {
        this.tokenKey = 'auth_token';
        this.tokenTypeKey = 'token_type';
        this.userKey = 'user';
        this.expiresAtKey = 'expires_at';
        
        // Verificar token al inicializar
        this.initAuth();
    }
    
    /**
     * Inicializa la autenticación
     */
    initAuth() {
        // Agregar eventos de autenticación global para fetch
        this.setupFetchInterceptor();
        
        // Actualizar UI según estado de autenticación
        this.updateAuthUI();
        
        // Verificar si el token está por expirar cada minuto
        setInterval(() => this.checkTokenExpiry(), 60000);
    }
    
    /**
     * Configura interceptor para fetch para añadir token a todas las peticiones
     */
    setupFetchInterceptor() {
        const originalFetch = window.fetch;
        
        window.fetch = async (url, options = {}) => {
            // No añadir token a peticiones a otras URLs o a rutas de autenticación
            if (typeof url === 'string' && 
                !url.includes('/api/auth/login') && 
                !url.includes('/api/auth/register') && 
                !url.includes('/api/auth/token')) {
                
                // Obtener token
                const token = this.getToken();
                const tokenType = this.getTokenType();
                
                if (token && tokenType) {
                    // Configurar headers si no existen
                    options.headers = options.headers || {};
                    
                    // Añadir token al header Authorization
                    options.headers['Authorization'] = `${tokenType} ${token}`;
                }
            }
            
            // Realizar la petición original
            return originalFetch(url, options).then(async response => {
                // Si hay error 401 (Unauthorized), intentar redireccionar a login
                if (response.status === 401) {
                    console.warn("Sesión expirada o token inválido");
                    
                    // Si la respuesta es JSON, clonarla para no consumirla
                    let isJSON = false;
                    let responseData = null;
                    
                    if (response.headers.get('content-type')?.includes('application/json')) {
                        isJSON = true;
                        // Clonar la respuesta para no consumirla
                        const clonedResponse = response.clone();
                        responseData = await clonedResponse.json();
                    }
                    
                    // Si estamos en una petición de API (no HTML), manejar según el caso
                    if (!window.location.pathname.startsWith('/ui/')) {
                        // Si es una petición AJAX, no redireccionar, solo limpiar tokens
                        this.clearAuth();
                    } else {
                        // Si estamos en la UI y no es login/register, redireccionar
                        if (!window.location.pathname.includes('/login') && 
                            !window.location.pathname.includes('/register')) {
                            this.redirectToLogin();
                        }
                    }
                    
                    // Si la respuesta es JSON, recrear una respuesta con los mismos datos
                    if (isJSON) {
                        return new Response(JSON.stringify(responseData), {
                            status: response.status,
                            statusText: response.statusText,
                            headers: response.headers
                        });
                    }
                }
                
                return response;
            }).catch(error => {
                console.error("Error en fetch:", error);
                throw error;
            });
        };
    }
    
    /**
     * Guarda los datos de autenticación
     */
    saveAuth(authData) {
        if (!authData || !authData.access_token) {
            console.error("Datos de autenticación inválidos");
            return false;
        }
        
        // Guardar token, tipo y datos de usuario
        localStorage.setItem(this.tokenKey, authData.access_token);
        localStorage.setItem(this.tokenTypeKey, authData.token_type || 'Bearer');
        
        if (authData.user) {
            localStorage.setItem(this.userKey, JSON.stringify(authData.user));
        }
        
        // Calcular tiempo de expiración
        if (authData.expires_in) {
            const expiresAt = new Date();
            expiresAt.setSeconds(expiresAt.getSeconds() + authData.expires_in);
            localStorage.setItem(this.expiresAtKey, expiresAt.toISOString());
        }
        
        // Actualizar la UI
        this.updateAuthUI();
        
        return true;
    }
    
    /**
     * Limpia los datos de autenticación
     */
    clearAuth() {
        localStorage.removeItem(this.tokenKey);
        localStorage.removeItem(this.tokenTypeKey);
        localStorage.removeItem(this.userKey);
        localStorage.removeItem(this.expiresAtKey);
        
        // Actualizar la UI
        this.updateAuthUI();
    }
    
    /**
     * Obtiene el token actual
     */
    getToken() {
        return localStorage.getItem(this.tokenKey);
    }
    
    /**
     * Obtiene el tipo de token
     */
    getTokenType() {
        return localStorage.getItem(this.tokenTypeKey) || 'Bearer';
    }
    
    /**
     * Obtiene el usuario actual
     */
    getUser() {
        const userJson = localStorage.getItem(this.userKey);
        if (!userJson) return null;
        
        try {
            return JSON.parse(userJson);
        } catch (e) {
            console.error("Error al parsear datos de usuario:", e);
            return null;
        }
    }
    
    /**
     * Verifica si el usuario está autenticado
     */
    isAuthenticated() {
        const token = this.getToken();
        if (!token) return false;
        
        // Verificar si el token ha expirado
        const expiresAt = localStorage.getItem(this.expiresAtKey);
        if (expiresAt) {
            const now = new Date();
            const expiry = new Date(expiresAt);
            
            if (now >= expiry) {
                console.log("Token expirado");
                this.clearAuth();
                return false;
            }
        }
        
        return true;
    }
    
    /**
     * Verifica si el token está por expirar (menos de 5 minutos)
     */
    checkTokenExpiry() {
        if (!this.isAuthenticated()) return;
        
        const expiresAt = localStorage.getItem(this.expiresAtKey);
        if (!expiresAt) return;
        
        const now = new Date();
        const expiry = new Date(expiresAt);
        const fiveMinutes = 5 * 60 * 1000; // 5 minutos en milisegundos
        
        if (expiry - now < fiveMinutes) {
            console.log("Token por expirar, renovando...");
            this.refreshToken();
        }
    }
    
    /**
     * Renueva el token (si es posible)
     */
    async refreshToken() {
        // Esta implementación depende de tu backend
        // Algunas APIs tienen un endpoint específico para renovar tokens
        
        try {
            // Ejemplo de endpoint de renovación
            const response = await fetch('/api/auth/refresh', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `${this.getTokenType()} ${this.getToken()}`
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                this.saveAuth(data);
                console.log("Token renovado exitosamente");
            } else {
                console.error("Error al renovar token:", response.status);
                
                // Si la API no soporta renovación, simplemente limpiar auth
                if (response.status === 401) {
                    this.clearAuth();
                    this.redirectToLogin();
                }
            }
        } catch (error) {
            console.error("Error al renovar token:", error);
        }
    }
    
    /**
     * Actualiza la UI según el estado de autenticación
     */
    updateAuthUI() {
        const isAuth = this.isAuthenticated();
        const user = this.getUser();
        
        // Elementos que se muestran solo a usuarios autenticados
        const authElements = document.querySelectorAll('.auth-only');
        // Elementos que se muestran solo a usuarios no autenticados
        const noAuthElements = document.querySelectorAll('.no-auth-only');
        // Elemento para mostrar nombre de usuario
        const userNameElements = document.querySelectorAll('.user-name');
        
        // Actualizar visibilidad según autenticación
        authElements.forEach(el => {
            el.style.display = isAuth ? '' : 'none';
        });
        
        noAuthElements.forEach(el => {
            el.style.display = isAuth ? 'none' : '';
        });
        
        // Actualizar nombre de usuario si está disponible
        if (user && userNameElements) {
            userNameElements.forEach(el => {
                el.textContent = user.username || user.full_name || 'Usuario';
            });
        }
        
        // Actualizar enlaces de admin si el usuario es administrador
        if (isAuth && user && user.is_admin) {
            const adminElements = document.querySelectorAll('.admin-only');
            adminElements.forEach(el => {
                el.style.display = '';
            });
        } else {
            const adminElements = document.querySelectorAll('.admin-only');
            adminElements.forEach(el => {
                el.style.display = 'none';
            });
        }
    }
    
    /**
     * Redirecciona a la página de login
     */
    redirectToLogin() {
        // Guardar la URL actual para redireccionar después del login
        const currentPath = window.location.pathname;
        if (currentPath !== '/ui/login' && currentPath !== '/ui/register') {
            localStorage.setItem('auth_redirect', currentPath);
        }
        
        // Redireccionar a login
        window.location.href = '/ui/login';
    }
    
    /**
     * Función de logout
     */
    logout() {
        this.clearAuth();
        window.location.href = '/ui/logout';
    }
}

// Crear instancia global
const authManager = new AuthManager();

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
    // Configurar botón de logout
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', function(e) {
            e.preventDefault();
            authManager.logout();
        });
    }
    
    // Si estamos en la página de login, configurar redirección después del login
    if (window.location.pathname === '/ui/login') {
        const redirectTo = localStorage.getItem('auth_redirect');
        if (redirectTo) {
            // Limpiar la URL de redirección
            localStorage.removeItem('auth_redirect');
            
            // Si el usuario ya está autenticado, redireccionar
            if (authManager.isAuthenticated()) {
                window.location.href = redirectTo;
            }
        }
    }
});

// Exponer globalmente
window.authManager = authManager;

// En login.html
document.getElementById('loginForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    
    try {
        const response = await fetch('/api/auth/token', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, password })
        });
        
        if (!response.ok) {
            throw new Error('Credenciales incorrectas');
        }
        
        const data = await response.json();
        
        // Guardar token en localStorage
        localStorage.setItem('auth_token', data.access_token);
        localStorage.setItem('token_type', data.token_type);
        localStorage.setItem('user', JSON.stringify(data.user));
        
        // Redireccionar a la página principal
        window.location.href = '/ui/';
    } catch (error) {
        // Mostrar error
        console.error('Error de login:', error);
        alert('Error de login: ' + error.message);
    }
});

// En auth.js
const originalFetch = window.fetch;
window.fetch = async (url, options = {}) => {
    const token = localStorage.getItem('auth_token');
    const tokenType = localStorage.getItem('token_type') || 'Bearer';
    
    if (token) {
        options.headers = options.headers || {};
        options.headers['Authorization'] = `${tokenType} ${token}`;
    }
    
    return originalFetch(url, options);
};