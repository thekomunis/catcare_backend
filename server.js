require("dotenv").config();
const Hapi = require("@hapi/hapi");
const axios = require("axios");
const FormData = require("form-data");
const { Pool } = require("pg");
const bcrypt = require("bcrypt");

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl:
    process.env.NODE_ENV === "production"
      ? { rejectUnauthorized: false }
      : false,
});

const init = async () => {
  const server = Hapi.server({
    port: 3000,
    host: "localhost",
    routes: {
      cors: {
        origin: ["*"],
        additionalHeaders: ["cache-control", "x-requested-with"],
      },
    },
  });

  // REGISTER
  server.route({
    method: "POST",
    path: "/register",
    handler: async (request, h) => {
      const { name, email, password } = request.payload;
      const hashed = await bcrypt.hash(password, 10);
      try {
        const existing = await pool.query(
          "SELECT * FROM users WHERE email = $1",
          [email]
        );
        if (existing.rows.length) {
          return h.response({ error: "Email already registered." }).code(400);
        }

        const res = await pool.query(
          "INSERT INTO users (name, email, password) VALUES ($1, $2, $3) RETURNING id, name, email",
          [name, email, hashed]
        );
        return res.rows[0];
      } catch (err) {
        console.error(err);
        return h.response({ error: "Registration failed." }).code(500);
      }
    },
  });

  // LOGIN
  server.route({
    method: "POST",
    path: "/login",
    handler: async (request, h) => {
      const { email, password } = request.payload;
      try {
        const user = await pool.query("SELECT * FROM users WHERE email = $1", [
          email,
        ]);
        if (
          !user.rows.length ||
          !(await bcrypt.compare(password, user.rows[0].password))
        ) {
          return h.response({ error: "Invalid credentials." }).code(401);
        }
        return result.rows[0];
      } catch (err) {
        console.error(err);
        return h.response({ error: "Login failed." }).code(500);
      }
    },
  });

  // PREDICT FORM
  server.route({
    method: "POST",
    path: "/predict",
    handler: async (request, h) => {
      const { userId, data } = request.payload;
      console.log(`Received prediction request from user ${userId}`);
      console.log(`Data: ${JSON.stringify(data)}`);
      try {
        const response = await axios.post(
          "https://cungsstore-catcare-apii.hf.space/predict",
          {
            data,
          }
        );
        const result = response.data.prediction || "No prediction";

        await pool.query(
          "INSERT INTO history (user_id, method, input, result) VALUES ($1, 'form', $2, $3)",
          [userId, JSON.stringify(data), result]
        );

        return response.data;
      } catch (err) {
        console.error("🔥 /predict error:", err.message);
        return h.response({ error: "Prediction failed." }).code(500);
      }
    },
  });

  // PREDICT IMAGE
  server.route({
    method: "POST",
    path: "/predict-image",
    options: {
      payload: {
        output: "stream",
        parse: true,
        multipart: true,
        maxBytes: 5 * 1024 * 1024,
      },
    },
    handler: async (request, h) => {
      try {
        const { file, userId } = request.payload;

        if (!file || !userId) {
          return h.response({ error: "Missing file or userId" }).code(400);
        }

        const formData = new FormData();
        formData.append("file", file._data, {
          filename: file.hapi.filename,
          contentType: file.hapi.headers["content-type"],
        });

        const response = await axios.post(
          "https://cungsstore-catcare-apii.hf.space/predict-image",
          formData,
          { headers: formData.getHeaders() }
        );

        const result = response.data.prediction || "No result";

        // Insert ke history
        await pool.query(
          "INSERT INTO history (user_id, method, input, result) VALUES ($1, 'image', $2, $3)",
          [userId, JSON.stringify({ filename: file.hapi.filename }), result]
        );

        return response.data;
      } catch (err) {
        console.error("🔥 /predict-image error:", err.message);
        return h.response({ error: "Image prediction failed." }).code(500);
      }
    },
  });

  await server.start();
  console.log("🚀 Server running at:", server.info.uri);
};

init();
