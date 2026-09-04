--
-- PostgreSQL database dump
--
-- Dumped from database version 18.4
-- Dumped by pg_dump version 18.4
SET statement_timeout = 0;
--
-- Limpiar tablas existentes en Supabase (CASCADE para evitar dependencias FK)
--
DROP TABLE IF EXISTS public.venta_detalle CASCADE;
DROP TABLE IF EXISTS public.ventas CASCADE;
DROP TABLE IF EXISTS public.movimientos CASCADE;
DROP TABLE IF EXISTS public.bitacora CASCADE;
DROP TABLE IF EXISTS public.productos CASCADE;
DROP TABLE IF EXISTS public.clientes CASCADE;
DROP TABLE IF EXISTS public.bodegas CASCADE;
DROP TABLE IF EXISTS public.usuarios CASCADE;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;
--
-- Name: public; Type: SCHEMA; Schema: -; Owner: -
--
SET default_tablespace = '';
SET default_table_access_method = heap;
--
-- Name: bitacora; Type: TABLE; Schema: public; Owner: -
--
CREATE TABLE public.bitacora (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    usuario_id uuid NOT NULL,
    accion text NOT NULL,
    detalles jsonb,
    fecha timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    dirty boolean DEFAULT true,
    synced_at timestamp with time zone
);
--
-- Name: bodegas; Type: TABLE; Schema: public; Owner: -
--
CREATE TABLE public.bodegas (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    nombre character varying(100) NOT NULL,
    ubicacion text,
    creado_en timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    dirty boolean DEFAULT true,
    synced_at timestamp with time zone
);
--
-- Name: clientes; Type: TABLE; Schema: public; Owner: -
--
CREATE TABLE public.clientes (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    nombre character varying(100) NOT NULL,
    telefono character varying(20),
    email character varying(100),
    creado_en timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    dirty boolean DEFAULT true,
    synced_at timestamp with time zone
);
--
-- Name: movimientos; Type: TABLE; Schema: public; Owner: -
--
CREATE TABLE public.movimientos (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    producto_id uuid NOT NULL,
    bodega_id uuid NOT NULL,
    usuario_id uuid NOT NULL,
    tipo character varying(20) NOT NULL,
    cantidad integer NOT NULL,
    fecha timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    motivo character varying(150),
    dirty boolean DEFAULT true,
    synced_at timestamp with time zone,
    CONSTRAINT movimientos_cantidad_check CHECK ((cantidad > 0)),
    CONSTRAINT movimientos_tipo_check CHECK (
        (
            (tipo)::text = ANY (
                (
                    ARRAY ['ingreso'::character varying, 'egreso'::character varying, 'transferencia'::character varying]
                )::text []
            )
        )
    )
);
--
-- Name: productos; Type: TABLE; Schema: public; Owner: -
--
CREATE TABLE public.productos (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    bodega_id uuid NOT NULL,
    nombre character varying(100) NOT NULL,
    descripcion text,
    sku character varying(50) NOT NULL,
    precio numeric(10, 2) NOT NULL,
    stock_actual integer DEFAULT 0 NOT NULL,
    creado_en timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    dirty boolean DEFAULT true,
    synced_at timestamp with time zone,
    CONSTRAINT productos_precio_check CHECK ((precio >= (0)::numeric)),
    CONSTRAINT productos_stock_actual_check CHECK ((stock_actual >= 0))
);
--
-- Name: usuarios; Type: TABLE; Schema: public; Owner: -
--
CREATE TABLE public.usuarios (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    name character varying(100) CONSTRAINT usuarios_nombre_not_null NOT NULL,
    email character varying(100) NOT NULL,
    rol character varying(20) NOT NULL,
    creado_en timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    password_hash character varying,
    CONSTRAINT usuarios_rol_check CHECK (
        (
            (rol)::text = ANY (
                (
                    ARRAY ['administrador'::character varying, 'empleado'::character varying]
                )::text []
            )
        )
    )
);
--
-- Name: venta_detalle; Type: TABLE; Schema: public; Owner: -
--
CREATE TABLE public.venta_detalle (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    venta_id uuid NOT NULL,
    producto_id uuid NOT NULL,
    cantidad integer NOT NULL,
    precio_unitario numeric(10, 2) NOT NULL,
    subtotal numeric(10, 2) NOT NULL,
    CONSTRAINT venta_detalle_cantidad_check CHECK ((cantidad > 0)),
    CONSTRAINT venta_detalle_precio_unitario_check CHECK ((precio_unitario >= (0)::numeric)),
    CONSTRAINT venta_detalle_subtotal_check CHECK ((subtotal >= (0)::numeric))
);
--
-- Name: ventas; Type: TABLE; Schema: public; Owner: -
--
CREATE TABLE public.ventas (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    cliente_id uuid NOT NULL,
    usuario_id uuid NOT NULL,
    total numeric(10, 2) DEFAULT 0.00 NOT NULL,
    fecha timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    dirty boolean DEFAULT true,
    synced_at timestamp with time zone,
    CONSTRAINT ventas_total_check CHECK ((total >= (0)::numeric))
);
--
-- Name: bitacora bitacora_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--
ALTER TABLE ONLY public.bitacora
ADD CONSTRAINT bitacora_pkey PRIMARY KEY (id);
--
-- Name: bodegas bodegas_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--
ALTER TABLE ONLY public.bodegas
ADD CONSTRAINT bodegas_pkey PRIMARY KEY (id);
--
-- Name: clientes clientes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--
ALTER TABLE ONLY public.clientes
ADD CONSTRAINT clientes_pkey PRIMARY KEY (id);
--
-- Name: movimientos movimientos_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--
ALTER TABLE ONLY public.movimientos
ADD CONSTRAINT movimientos_pkey PRIMARY KEY (id);
--
-- Name: productos productos_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--
ALTER TABLE ONLY public.productos
ADD CONSTRAINT productos_pkey PRIMARY KEY (id);
--
-- Name: productos productos_sku_key; Type: CONSTRAINT; Schema: public; Owner: -
--
ALTER TABLE ONLY public.productos
ADD CONSTRAINT productos_sku_key UNIQUE (sku);
--
-- Name: usuarios usuarios_email_key; Type: CONSTRAINT; Schema: public; Owner: -
--
ALTER TABLE ONLY public.usuarios
ADD CONSTRAINT usuarios_email_key UNIQUE (email);
--
-- Name: usuarios usuarios_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--
ALTER TABLE ONLY public.usuarios
ADD CONSTRAINT usuarios_name_key UNIQUE (name);
--
-- Name: usuarios usuarios_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--
ALTER TABLE ONLY public.usuarios
ADD CONSTRAINT usuarios_pkey PRIMARY KEY (id);
--
-- Name: venta_detalle venta_detalle_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--
ALTER TABLE ONLY public.venta_detalle
ADD CONSTRAINT venta_detalle_pkey PRIMARY KEY (id);
--
-- Name: ventas ventas_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--
ALTER TABLE ONLY public.ventas
ADD CONSTRAINT ventas_pkey PRIMARY KEY (id);
--
-- Name: idx_bitacora_usuario; Type: INDEX; Schema: public; Owner: -
--
CREATE INDEX idx_bitacora_usuario ON public.bitacora USING btree (usuario_id);
--
-- Name: idx_movimientos_bodega; Type: INDEX; Schema: public; Owner: -
--
CREATE INDEX idx_movimientos_bodega ON public.movimientos USING btree (bodega_id);
--
-- Name: idx_movimientos_fecha; Type: INDEX; Schema: public; Owner: -
--
CREATE INDEX idx_movimientos_fecha ON public.movimientos USING btree (fecha);
--
-- Name: idx_movimientos_producto; Type: INDEX; Schema: public; Owner: -
--
CREATE INDEX idx_movimientos_producto ON public.movimientos USING btree (producto_id);
--
-- Name: idx_movimientos_usuario; Type: INDEX; Schema: public; Owner: -
--
CREATE INDEX idx_movimientos_usuario ON public.movimientos USING btree (usuario_id);
--
-- Name: idx_productos_bodega; Type: INDEX; Schema: public; Owner: -
--
CREATE INDEX idx_productos_bodega ON public.productos USING btree (bodega_id);
--
-- Name: idx_venta_detalle_producto; Type: INDEX; Schema: public; Owner: -
--
CREATE INDEX idx_venta_detalle_producto ON public.venta_detalle USING btree (producto_id);
--
-- Name: idx_venta_detalle_venta; Type: INDEX; Schema: public; Owner: -
--
CREATE INDEX idx_venta_detalle_venta ON public.venta_detalle USING btree (venta_id);
--
-- Name: idx_ventas_cliente; Type: INDEX; Schema: public; Owner: -
--
CREATE INDEX idx_ventas_cliente ON public.ventas USING btree (cliente_id);
--
-- Name: idx_ventas_fecha; Type: INDEX; Schema: public; Owner: -
--
CREATE INDEX idx_ventas_fecha ON public.ventas USING btree (fecha);
--
-- Name: idx_ventas_usuario; Type: INDEX; Schema: public; Owner: -
--
CREATE INDEX idx_ventas_usuario ON public.ventas USING btree (usuario_id);
--
-- Name: bitacora bitacora_usuario_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--
ALTER TABLE ONLY public.bitacora
ADD CONSTRAINT bitacora_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES public.usuarios(id) ON DELETE
SET NULL;
--
-- Name: movimientos movimientos_bodega_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--
ALTER TABLE ONLY public.movimientos
ADD CONSTRAINT movimientos_bodega_id_fkey FOREIGN KEY (bodega_id) REFERENCES public.bodegas(id) ON DELETE RESTRICT;
--
-- Name: movimientos movimientos_producto_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--
ALTER TABLE ONLY public.movimientos
ADD CONSTRAINT movimientos_producto_id_fkey FOREIGN KEY (producto_id) REFERENCES public.productos(id) ON DELETE CASCADE;
--
-- Name: movimientos movimientos_usuario_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--
ALTER TABLE ONLY public.movimientos
ADD CONSTRAINT movimientos_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES public.usuarios(id) ON DELETE RESTRICT;
--
-- Name: productos productos_bodega_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--
ALTER TABLE ONLY public.productos
ADD CONSTRAINT productos_bodega_id_fkey FOREIGN KEY (bodega_id) REFERENCES public.bodegas(id) ON DELETE RESTRICT;
--
-- Name: venta_detalle venta_detalle_producto_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--
ALTER TABLE ONLY public.venta_detalle
ADD CONSTRAINT venta_detalle_producto_id_fkey FOREIGN KEY (producto_id) REFERENCES public.productos(id) ON DELETE RESTRICT;
--
-- Name: venta_detalle venta_detalle_venta_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--
ALTER TABLE ONLY public.venta_detalle
ADD CONSTRAINT venta_detalle_venta_id_fkey FOREIGN KEY (venta_id) REFERENCES public.ventas(id) ON DELETE CASCADE;
--
-- Name: ventas ventas_cliente_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--
ALTER TABLE ONLY public.ventas
ADD CONSTRAINT ventas_cliente_id_fkey FOREIGN KEY (cliente_id) REFERENCES public.clientes(id) ON DELETE RESTRICT;
--
-- Name: ventas ventas_usuario_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--
ALTER TABLE ONLY public.ventas
ADD CONSTRAINT ventas_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES public.usuarios(id) ON DELETE RESTRICT;
--
-- PostgreSQL database dump complete
--
--
-- Permisos para PostgREST / Supabase API
--
GRANT USAGE ON SCHEMA public TO anon,
    authenticated;
GRANT ALL ON ALL TABLES IN SCHEMA public TO anon,
    authenticated;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO anon,
    authenticated;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT ALL ON TABLES TO anon,
    authenticated;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT ALL ON SEQUENCES TO anon,
    authenticated;
-- Recargar schema cache de PostgREST
NOTIFY pgrst,
'reload schema';