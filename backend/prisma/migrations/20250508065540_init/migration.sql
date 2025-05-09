-- CreateTable
CREATE TABLE "SiteConfig" (
    "id" SERIAL NOT NULL,
    "name" TEXT NOT NULL,
    "description" TEXT,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "SiteConfig_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "SiteConfigDetail" (
    "id" SERIAL NOT NULL,
    "site_config_id" INTEGER NOT NULL,
    "item" TEXT NOT NULL,
    "word_style_name" TEXT NOT NULL,
    "html_tag" TEXT NOT NULL,
    "html_class" TEXT NOT NULL,
    "html_style" TEXT NOT NULL,
    "prefix_text" TEXT NOT NULL,
    "suffix_text" TEXT NOT NULL,

    CONSTRAINT "SiteConfigDetail_pkey" PRIMARY KEY ("id")
);

-- AddForeignKey
ALTER TABLE "SiteConfigDetail" ADD CONSTRAINT "SiteConfigDetail_site_config_id_fkey" FOREIGN KEY ("site_config_id") REFERENCES "SiteConfig"("id") ON DELETE CASCADE ON UPDATE CASCADE;
