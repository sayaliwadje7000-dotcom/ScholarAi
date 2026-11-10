# ScholarAI Phase 18.7 â€” Role-Based Access Control

## 1. Objective

Implement database-backed role-based access control for ScholarAI.

## 2. Supported roles

### Student
- Access student learning functionality.
- Access educational resources.
- Access personal recommendations.

### Educator
- Student-level access when assigned both roles.
- Access designated educator functionality.

### Administrator
- Administrative user management.
- Role assignment.
- Role revocation.
- Administrative API access.

## 3. Architecture

Authorization flow:

1. Client sends an authenticated request.
2. JWT authentication dependency validates the access token.
3. Persistent session validation confirms the session is active.
4. get_current_user resolves the authenticated user.
5. require_roles loads the user's database roles.
6. The permission dependency checks the required role.
7. The request is allowed or rejected.

## 4. Database

Table: user_roles

Columns:
- id
- user_id
- role
- created_at

Constraints:
- UUID primary key.
- Foreign key to users.id.
- Unique user_id and role combination.
- Cascade deletion when the user is deleted.

## 5. API

GET /api/v1/admin/users/{user_id}/roles

POST /api/v1/admin/users/{user_id}/roles

DELETE /api/v1/admin/users/{user_id}/roles/{role}

## 6. Authorization dependencies

- require_student
- require_educator
- require_admin
- require_educator_or_admin

## 7. Security controls

- Role assignment requires administrator authorization.
- Public registration cannot assign administrative privileges.
- Unknown roles are rejected.
- Duplicate role assignment is rejected.
- Last administrator cannot be removed through the role service.
- Roles are queried from the database instead of trusting JWT role claims.
- Role revocation takes effect on subsequent authorization checks.

## 8. Initial administrator

The first administrator must be provisioned through the controlled command:

python -m scripts.provision_admin student@example.com

Replace the email with an existing registered account.

## 9. Testing

Run:

python -m pytest tests/auth/test_rbac.py -v

Then run the full test suite:

python -m pytest -v

## 10. Remaining security work

Phase 18.8 will apply authorization dependencies to protected API routes.

Phase 18.10 will perform broader security hardening, including rate limiting and additional abuse controls.
