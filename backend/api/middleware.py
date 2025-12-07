"""
Security middleware for PlanningJam API.

Includes:
- Content Security Policy (CSP) header middleware
"""

from django.conf import settings


class CSPMiddleware:
    """
    Middleware to set Content Security Policy (CSP) headers.
    
    CSP is a security policy that helps prevent:
    - Cross-Site Scripting (XSS) attacks
    - Data injection attacks
    - Clickjacking
    - Other content injection attacks
    
    The policy is defined in settings.CSP_DIRECTIVES and can be controlled via:
    - CSP_ENABLED setting (enable/disable the middleware)
    - CSP_DIRECTIVES dict for specific policy directives
    - CSP_REPORT_ONLY setting (report violations without blocking)
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.csp_enabled = getattr(settings, 'CSP_ENABLED', True)
        self.csp_directives = getattr(settings, 'CSP_DIRECTIVES', {})
        self.csp_report_only = getattr(settings, 'CSP_REPORT_ONLY', False)
    
    def __call__(self, request):
        response = self.get_response(request)
        
        if self.csp_enabled and self.csp_directives:
            csp_header = self._build_csp_header()
            
            # Use Content-Security-Policy header for enforcement
            # or Content-Security-Policy-Report-Only for monitoring (no blocking)
            header_name = 'Content-Security-Policy-Report-Only' if self.csp_report_only else 'Content-Security-Policy'
            response[header_name] = csp_header
        
        return response
    
    def _build_csp_header(self) -> str:
        """
        Build CSP header string from directives.
        
        Returns:
            CSP header value (e.g., "default-src 'self'; script-src 'self' 'unsafe-inline'")
        """
        directives = []
        
        for directive, values in self.csp_directives.items():
            # Convert list of values to space-separated string
            if isinstance(values, list):
                values_str = ' '.join(values)
            else:
                values_str = str(values)
            
            directives.append(f"{directive} {values_str}")
        
        return '; '.join(directives)
