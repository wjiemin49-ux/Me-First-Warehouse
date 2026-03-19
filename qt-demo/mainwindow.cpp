#include "mainwindow.h"
#include "ui_mainwindow.h"
#include <QFileDialog>
#include <QMessageBox>

MainWindow::MainWindow(QWidget *parent)
    : QMainWindow(parent)
    , ui(new Ui::MainWindow)
{
    ui->setupUi(this);
    setWindowTitle("Qt 示例应用");
}

MainWindow::~MainWindow()
{
    delete ui;
}

void MainWindow::on_testButton_clicked()
{
    ui->statusLabel->setText("测试按钮已点击，这是来自 C++ 后端的响应");
    QMessageBox::information(this, "测试", "Qt 示例应用测试成功！");
}

void MainWindow::on_openFileButton_clicked()
{
    QString fileName = QFileDialog::getOpenFileName(this, "打开文件", "", "文本文件 (*.txt);;所有文件 (*.*)");
    if (!fileName.isEmpty()) {
        ui->filePathLabel->setText(fileName);
        ui->fileInfoGroupBox->setVisible(true);
    }
}