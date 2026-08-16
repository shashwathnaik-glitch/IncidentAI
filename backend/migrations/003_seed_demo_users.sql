-- Seed default demo users for local development and clean checkouts
INSERT INTO users (id, email, password_hash, role, name, department)
VALUES 
  ('12a31830-ef2f-4697-8e8c-ffbc816fdcd3', 'employee@company.com', '$2b$12$smeTSjjWUu30gidTt382le.K6DXmBjEl0fIS5pc7ApFRccbaDMTcy', 'employee', 'Alex Rivera', 'IT Support'),
  ('61d48c23-ab03-4064-9871-719aa0085c92', 'admin@company.com', '$2b$12$JEgQS3Gii9fbS0M5Hq4GVO1fPmxmQhlTnE2PzatpOSq/kUfCbSfya', 'admin', 'Admin User', 'IT Operations')
ON CONFLICT (email) DO NOTHING;
