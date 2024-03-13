import backtrader as bt
import yfinance as yf
import csv


class Estrategia(bt.Strategy):
    params = (
        ('outputPath', "./output.csv"),  # Path para guardar el csv de salida
    )

    def __init__(self):
        self.resetCsv(self.params.outputPath) #Inicializo el archivo de salida
        self.estrategias = ["Valor de cierre vs SMA10", "Valor de cierre vs SMA30", "Cruces de SMA10 y SMA30"]

        # Matriz para guardar las acciones compradas por cada empresa y con cada estrategia.
        # Esta matriz me servirá para que solo se puedan vender las acciones de una empresa utilizando la misma
        # estrategia con la que se compró.
        self.registro = {name._name: {estrategia: 0 for estrategia in self.estrategias} for name in self.datas} 
        self.porcentaje_inversion = 0.10 
        
        #Creo los indicadores SMA para cada empresa 
        self.sma_10 = dict()
        self.sma_30 = dict()
        for empresa in self.datas:
            self.sma_10[empresa._name] = bt.indicators.SimpleMovingAverage(empresa, period=10)
            self.sma_30[empresa._name] = bt.indicators.SimpleMovingAverage(empresa, period=30)

    #Inicializa el archivo de salida con el header
    def resetCsv(self, path):
        header = ['Empresa', 'Operacion', 'Cantidad', 'Estrategia', 'Valor portafolio']
        with open(path, 'w') as f:
            csv.writer(f).writerow(header)

    def escribir_archivo(self, row):
        with open(self.params.outputPath, 'a') as f:
            csv.writer(f).writerow(row)

    def registrar_compra(self, estrategia, empresa):
        valor_total_cartera = self.broker.get_value()
        efectivo_disponible = self.broker.get_cash()
        
        inversion_actual = valor_total_cartera * self.porcentaje_inversion # Calculo el monto que debo invertir en la compra

        if efectivo_disponible >= inversion_actual:  # Verifico si hay suficiente efectivo para la compra
            # Calculo la cantidad de acciones y realizo la compra
            cantidad_compra = int(inversion_actual / empresa.close[0])
            self.buy(size=cantidad_compra, data=empresa)

            self.registro[empresa._name][estrategia] += cantidad_compra # Actualizo la cantidad de acciones compradas de la empresa utilizando la estrategia
            self.escribir_archivo([empresa._name, 'Compra', cantidad_compra, estrategia, valor_total_cartera])


    def registrar_venta(self, estrategia, empresa):
        cantidad = self.registro[empresa._name][estrategia] # Obtengo la cantidad de acciones que compré de la empresa utilizando la estrategia
        if(cantidad > 0):
            self.sell(size=cantidad, data=empresa)
            self.registro[empresa._name][estrategia] = 0 # Actualizo a cero la cantidad de acciones
            self.escribir_archivo([empresa._name, 'Venta', cantidad, estrategia, self.broker.get_value()])


    def next(self):
        # Itero los datos de cada una de las empresas para evaluarlos con cada estrategia
        for empresa in self.datas:
            name = empresa._name
            #PRIMERA ESTRATEGIA: Comprar cuando el precio supere la SMA de 10 y vender cuando el precio caiga por debajo de la SMA de 10
            if empresa.close[0] > self.sma_10[name][0] and empresa.close[-1] <= self.sma_10[name][-1]:
                self.registrar_compra(self.estrategias[0], empresa)

            elif empresa.close[0] < self.sma_10[name][0] and empresa.close[-1] >= self.sma_10[name][-1]:
                self.registrar_venta(self.estrategias[0], empresa)

            #SEGUNDA ESTRATEGIA: Comprar cuando el precio supere la SMA de 30 y vender cuando el precio caiga por debajo de la SMA de 30
            if empresa.close[0] > self.sma_30[name][0] and empresa.close[-1] <= self.sma_30[name][-1]:
                self.registrar_compra(self.estrategias[1], empresa)

            elif empresa.close[0] < self.sma_30[name][0] and empresa.close[-1] >= self.sma_30[name][-1]:
                self.registrar_venta(self.estrategias[1], empresa)

            #TERCERA ESTRATEGIA: comprar cuando la vela de 10 cruce sobre la vela de 30 superandola y vender cuando la vela de 30 cruce sobre la vela de 10 superandola
            if self.sma_10[name][0] > self.sma_30[name][0] and self.sma_10[name][-1] <= self.sma_30[name][-1]:
                self.registrar_compra(self.estrategias[2], empresa)

            elif self.sma_10[name][0] < self.sma_30[name][0] and self.sma_10[name][-1] >= self.sma_30[name][-1]:
                self.registrar_venta(self.estrategias[2], empresa)




def main():
    
    cerebro = bt.Cerebro()
    cerebro.addsizer(bt.sizers.PercentSizer, percents=10)

    symbols = ['MSFT', 'GOOG', 'AAPL', 'TSLA']
    for symbol in symbols:
        df = yf.download(symbol, start='2021-01-01', end='2021-12-31')
        feed = bt.feeds.PandasData(dataname=df)
        cerebro.adddata(feed, name=symbol)

    cerebro.addstrategy(Estrategia)

    cerebro.broker.setcash(100000.0)
    cerebro.run()

    cerebro.plot()


main()